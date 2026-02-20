# amino/rules/parser.py
import re
from collections.abc import Callable
from typing import Any

from amino.errors import RuleParseError
from amino.operators.registry import OperatorRegistry
from amino.schema.registry import SchemaRegistry

from .ast import BinaryOp, FunctionCall, Literal, RuleAST, RuleNode, UnaryOp, Variable

# ── tokenizer ──────────────────────────────────────────────────────────────────

_FLOAT_RE = re.compile(r"-?\d+\.\d+")
_INT_RE   = re.compile(r"-?\d+")
_STR_RE   = re.compile(r"'[^']*'")
_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

_FIXED_SYMBOLS = [">=", "<=", "!=", ">", "<", "=", "(", ")", "[", "]", ",", "."]


def _tokenize(text: str, op_symbols: set[str]) -> list[str]:
    all_symbols = sorted(op_symbols | set(_FIXED_SYMBOLS), key=len, reverse=True)
    tokens: list[str] = []
    i = 0
    while i < len(text):
        if text[i] in " \t":
            i += 1
            continue
        # Multi-word "not in"
        if text[i:i+6] == "not in":
            tokens.append("not in")
            i += 6
            continue
        # Strings
        m = _STR_RE.match(text, i)
        if m:
            tokens.append(m.group())
            i = m.end()
            continue
        # Float before int
        m = _FLOAT_RE.match(text, i)
        if m:
            tokens.append(m.group())
            i = m.end()
            continue
        m = _INT_RE.match(text, i)
        if m:
            tokens.append(m.group())
            i = m.end()
            continue
        # Identifiers / keywords
        m = _IDENT_RE.match(text, i)
        if m:
            tokens.append(m.group())
            i = m.end()
            continue
        # Symbols (longest match)
        matched = False
        for sym in all_symbols:
            if text[i:i+len(sym)] == sym:
                tokens.append(sym)
                i += len(sym)
                matched = True
                break
        if not matched:
            raise RuleParseError(f"Unexpected character '{text[i]}' at position {i}")
    return tokens


# ── parser ─────────────────────────────────────────────────────────────────────

class _PrattParser:
    def __init__(self, tokens: list[str], schema: SchemaRegistry, ops: OperatorRegistry):
        self._tokens = tokens
        self._pos = 0
        self._schema = schema
        self._ops = ops

    def _peek(self) -> str | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _advance(self) -> str:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _left_bp(self, token: str | None) -> int:
        if token is None:
            return 0
        bp = self._ops.get_binding_power(token)
        return bp if bp is not None else 0

    def parse(self) -> RuleAST:
        node = self._parse_expr(0)
        if self._pos < len(self._tokens):
            raise RuleParseError(f"Unexpected token: {self._tokens[self._pos]!r}")
        return RuleAST(root=node, return_type=node.type_name)

    def _parse_expr(self, min_bp: int) -> RuleNode:
        left = self._nud()
        while True:
            tok = self._peek()
            if tok is None or tok in (")", "]", ","):
                break
            # "not in" may arrive as a single token from the tokenizer,
            # or as two separate tokens "not" + "in" if the tokenizer emitted them separately.
            two_token_not_in = (
                tok == "not"
                and self._pos + 1 < len(self._tokens)
                and self._tokens[self._pos + 1] == "in"
            )
            if two_token_not_in:
                tok = "not in"
            bp = self._left_bp(tok)
            if bp <= min_bp:
                break
            if two_token_not_in:
                # consume "not" and "in" as separate tokens
                self._advance()
                self._advance()
            else:
                self._advance()
            left = self._led(tok, left)
        return left

    def _nud(self) -> RuleNode:
        tok = self._advance()

        # Parentheses
        if tok == "(":
            node = self._parse_expr(0)
            if self._peek() != ")":
                raise RuleParseError("Expected ')'")
            self._advance()
            return node

        # List literal
        if tok == "[":
            items: list[Any] = []
            while self._peek() != "]":
                items.append(self._parse_literal_value())
                if self._peek() == ",":
                    self._advance()
            self._advance()  # ]
            return Literal(items, "List")

        # Prefix operator (not, ~, etc.)
        op_def = self._ops.lookup_keyword(tok) or self._ops.lookup_symbol(tok)
        if op_def and op_def.kind == "prefix":
            operand = self._parse_expr(op_def.binding_power)
            fn: Callable = op_def.fn or (lambda v: not v)
            return UnaryOp(tok, operand, op_def.return_type, fn)

        # Float literal
        try:
            val = float(tok)
            if "." in tok:
                return Literal(val, "Float")
        except ValueError:
            pass

        # Integer literal
        try:
            return Literal(int(tok), "Int")
        except ValueError:
            pass

        # String literal
        if tok.startswith("'") and tok.endswith("'"):
            return Literal(tok[1:-1], "Str")

        # Boolean
        if tok == "true":
            return Literal(True, "Bool")
        if tok == "false":
            return Literal(False, "Bool")

        # Identifier: function call or variable (possibly dotted)
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", tok):
            # function call?
            if self._peek() == "(":
                return self._parse_func_call(tok)
            # dotted name?
            name = tok
            while self._peek() == ".":
                self._advance()
                part = self._advance()
                name = f"{name}.{part}"
            # resolve type from schema
            field = self._schema.get_field(name)
            if field is None:
                raise RuleParseError(f"Unknown field or variable: '{name}'")
            return Variable(name, field.type_name)

        raise RuleParseError(f"Unexpected token in expression: {tok!r}")

    def _led(self, tok: str, left: RuleNode) -> RuleNode:
        # Resolve operator with type dispatch
        right = self._parse_expr(self._left_bp(tok))
        left_type = left.type_name
        right_type = right.type_name
        op_def = (self._ops.lookup_by_types(tok, (left_type, right_type))
                  or self._ops.lookup_by_types(tok, ("*", "*")))
        if op_def is None:
            raise RuleParseError(f"No operator '{tok}' for types ({left_type}, {right_type})")

        # For and/or: implement inline with short-circuit (fn=None in registry)
        def _and(left_v: Any, right_v: Any) -> bool:
            return bool(left_v) and bool(right_v)

        def _or(left_v: Any, right_v: Any) -> bool:
            return bool(left_v) or bool(right_v)

        if tok == "and":
            fn_op: Callable = _and
        elif tok == "or":
            fn_op = _or
        else:
            fn_op = op_def.fn

        return BinaryOp(tok, left, right, op_def.return_type, fn_op)

    def _parse_func_call(self, name: str) -> FunctionCall:
        self._advance()  # (
        args: list[RuleNode] = []
        while self._peek() != ")":
            args.append(self._parse_expr(0))
            if self._peek() == ",":
                self._advance()
        self._advance()  # )
        # Resolve return type from schema functions
        fn_def = next((f for f in self._schema._ast.functions if f.name == name), None)
        return_type = fn_def.return_type_name if fn_def else "Any"
        return FunctionCall(name, args, return_type)

    def _parse_literal_value(self) -> Any:
        tok = self._peek()
        # Nested list literal
        if tok == "[":
            self._advance()  # consume "["
            items: list[Any] = []
            while self._peek() != "]":
                items.append(self._parse_literal_value())
                if self._peek() == ",":
                    self._advance()
            self._advance()  # consume "]"
            return items
        tok = self._advance()
        if tok.startswith("'"):
            return tok[1:-1]
        if tok == "true":
            return True
        if tok == "false":
            return False
        try:
            if "." in tok:
                return float(tok)
            return int(tok)
        except ValueError as err:
            raise RuleParseError(f"Expected literal, got {tok!r}") from err


def parse_rule(text: str, schema: SchemaRegistry, ops: OperatorRegistry) -> RuleAST:
    tokens = _tokenize(text.strip(), ops.all_symbols())
    return _PrattParser(tokens, schema, ops).parse()
