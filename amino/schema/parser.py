# amino/schema/parser.py
import re
from typing import Any
from .ast import FieldDefinition, FunctionDefinition, FunctionParameter, SchemaAST, SchemaType, StructDefinition
from amino.errors import SchemaParseError

_PRIMITIVES: dict[str, SchemaType] = {
    "Int": SchemaType.INT, "Float": SchemaType.FLOAT,
    "Str": SchemaType.STR, "Bool": SchemaType.BOOL,
}
_RESERVED = {"struct", "List"}


class _Parser:
    def __init__(self, text: str):
        self._text = text
        self._pos = 0
        self._line = 1

    def _peek(self) -> str | None:
        return self._text[self._pos] if self._pos < len(self._text) else None

    def _advance(self) -> str:
        ch = self._text[self._pos]
        if ch == "\n":
            self._line += 1
        self._pos += 1
        return ch

    def _skip_ws(self, newlines: bool = False) -> None:
        while self._pos < len(self._text):
            ch = self._text[self._pos]
            if ch == "#":
                while self._pos < len(self._text) and self._text[self._pos] != "\n":
                    self._pos += 1
            elif ch in " \t" or (newlines and ch in "\r\n"):
                if ch == "\n":
                    self._line += 1
                self._pos += 1
            else:
                break

    def _skip_h(self) -> None:  # horizontal only
        while self._pos < len(self._text) and self._text[self._pos] in " \t":
            self._pos += 1

    def _read_ident(self) -> str:
        m = re.match(r"[a-zA-Z_][a-zA-Z0-9_]*", self._text[self._pos:])
        if not m:
            raise SchemaParseError(f"Expected identifier at line {self._line}")
        self._pos += len(m.group())
        return m.group()

    def _expect(self, ch: str) -> None:
        self._skip_h()
        if self._peek() != ch:
            raise SchemaParseError(f"Expected '{ch}' at line {self._line}, got {self._peek()!r}")
        self._advance()

    # --- constraint values ---

    def _parse_str_literal(self) -> str:
        self._advance()  # opening '
        buf: list[str] = []
        while self._peek() not in (None, "'"):
            buf.append(self._advance())
        if self._peek() != "'":
            raise SchemaParseError(f"Unterminated string at line {self._line}")
        self._advance()
        return "".join(buf)

    def _parse_list_lit(self) -> list:
        self._advance()  # [
        items: list = []
        self._skip_h()
        while self._peek() != "]":
            items.append(self._parse_constraint_val())
            self._skip_h()
            if self._peek() == ",":
                self._advance()
                self._skip_h()
        self._advance()  # ]
        return items

    def _parse_constraint_val(self) -> Any:
        self._skip_h()
        ch = self._peek()
        if ch == "'":
            return self._parse_str_literal()
        if ch == "[":
            return self._parse_list_lit()
        m = re.match(r"-?\d+\.\d+", self._text[self._pos:])
        if m:
            self._pos += len(m.group())
            return float(m.group())
        m = re.match(r"-?\d+", self._text[self._pos:])
        if m:
            self._pos += len(m.group())
            return int(m.group())
        m = re.match(r"true|false", self._text[self._pos:])
        if m:
            self._pos += len(m.group())
            return m.group() == "true"
        raise SchemaParseError(f"Expected constraint value at line {self._line}")

    def _parse_constraints(self) -> dict[str, Any]:
        self._advance()  # {
        result: dict[str, Any] = {}
        self._skip_h()
        while self._peek() != "}":
            key = self._read_ident()
            self._expect(":")
            result[key] = self._parse_constraint_val()
            self._skip_h()
            if self._peek() == ",":
                self._advance()
                self._skip_h()
        self._advance()  # }
        return result

    # --- type expression ---

    def _parse_type_expr(self) -> tuple[SchemaType, str, list[str]]:
        self._skip_h()
        name = self._read_ident()
        if name == "List":
            self._expect("[")
            elems: list[str] = [self._read_ident()]
            while self._peek() == "|":
                self._advance()
                elems.append(self._read_ident())
            self._expect("]")
            return SchemaType.LIST, f"List[{'|'.join(elems)}]", elems
        if name in _PRIMITIVES:
            return _PRIMITIVES[name], name, []
        return SchemaType.CUSTOM, name, []

    # --- field ---

    def _parse_field(self) -> FieldDefinition:
        self._skip_h()
        name = self._read_ident()
        if name in _RESERVED:
            raise SchemaParseError(f"Reserved word '{name}' used as field name at line {self._line}")
        self._expect(":")
        stype, tname, elems = self._parse_type_expr()
        optional = False
        self._skip_h()
        if self._peek() == "?":
            optional = True
            self._advance()
        constraints: dict[str, Any] = {}
        self._skip_h()
        if self._peek() == "{":
            constraints = self._parse_constraints()
        return FieldDefinition(name, stype, tname, elems, constraints, optional)

    # --- struct ---

    def _parse_struct(self) -> StructDefinition:
        self._read_ident()  # 'struct'
        self._skip_h()
        name = self._read_ident()
        self._skip_ws(newlines=True)
        self._expect("{")
        fields: list[FieldDefinition] = []
        while True:
            self._skip_ws(newlines=True)
            if self._peek() == "}":
                break
            fields.append(self._parse_field())
            self._skip_h()
            if self._peek() == ",":
                self._advance()
        self._advance()  # }
        return StructDefinition(name, fields)

    # --- function ---

    def _is_function(self) -> bool:
        saved = self._pos
        try:
            self._read_ident()
            self._skip_h()
            if self._peek() != ":":
                return False
            self._advance()
            self._skip_h()
            return self._peek() == "("
        except SchemaParseError:
            return False
        finally:
            self._pos = saved

    def _parse_function(self) -> FunctionDefinition:
        name = self._read_ident()
        self._expect(":")
        self._expect("(")
        params: list[FunctionParameter] = []
        self._skip_h()
        while self._peek() != ")":
            pname = self._read_ident()
            self._expect(":")
            _, ptype_name, _ = self._parse_type_expr()
            params.append(FunctionParameter(pname, ptype_name))
            self._skip_h()
            if self._peek() == ",":
                self._advance()
                self._skip_h()
        self._advance()  # )
        self._skip_h()
        if self._text[self._pos:self._pos + 2] != "->":
            raise SchemaParseError(f"Expected '->' at line {self._line}")
        self._pos += 2
        self._skip_h()
        ret_name = self._read_ident()
        return FunctionDefinition(name, params, ret_name)

    # --- top-level ---

    def parse(self) -> SchemaAST:
        ast = SchemaAST()
        while True:
            self._skip_ws(newlines=True)
            if self._pos >= len(self._text):
                break
            if self._text[self._pos:].startswith("struct"):
                ast.structs.append(self._parse_struct())
            elif self._is_function():
                ast.functions.append(self._parse_function())
            else:
                ast.fields.append(self._parse_field())
        return ast


def parse_schema(text: str) -> SchemaAST:
    return _Parser(text).parse()
