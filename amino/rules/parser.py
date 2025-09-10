"""Rule parser implementation."""

import dataclasses
import enum
import re
from typing import List, Dict, Any, Optional, Union

from ..utils.errors import RuleParseError
from ..schema.ast import SchemaAST
from ..schema.types import SchemaType
from .ast import (
    RuleAST, RuleNode, BinaryOp, UnaryOp, Literal, Variable, 
    FunctionCall, Operator
)


# Token patterns
WHITESPACE = re.compile(r"[\s]+")
NAME = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
NUMBER = re.compile(r"\d+(\.\d+)?")
STRING = re.compile(r'"([^"\\\\]|\\\\.)*"|\'([^\'\\\\]|\\\\.)*\'')
LPAREN = re.compile(r"\(")
RPAREN = re.compile(r"\)")
COMMA = re.compile(r",")
DOT = re.compile(r"\.")

# Operators (order matters for multi-char ops)
OPERATORS = [
    (">=", Operator.GTE),
    ("<=", Operator.LTE), 
    ("!=", Operator.NE),
    ("not in", Operator.NOT_IN),
    (">", Operator.GT),
    ("<", Operator.LT),
    ("=", Operator.EQ),
    ("in", Operator.IN),
    ("and", Operator.AND),
    ("or", Operator.OR),
    ("not", Operator.NOT),
    ("typeof", Operator.TYPEOF),
    ("is_valid", Operator.IS_VALID),
]


class TokenType(enum.Enum):
    """Token types for rule parsing."""
    NAME = "name"
    NUMBER = "number"
    STRING = "string"
    OPERATOR = "operator"
    LPAREN = "lparen"
    RPAREN = "rparen"
    COMMA = "comma"
    DOT = "dot"


@dataclasses.dataclass
class Token:
    """Rule token."""
    type: TokenType
    value: str
    operator: Optional[Operator] = None


class RuleParser:
    """Parser for rule expressions."""
    
    def __init__(self, rule: str, schema_ast: SchemaAST):
        self.rule = rule
        self.schema_ast = schema_ast
        self.tokens = self._tokenize()
        self.pos = 0
        
        # Build lookup tables from schema
        self._variables = {f.name: f.field_type for f in schema_ast.fields}
        self._structs = {s.name: s for s in schema_ast.structs}
        self._functions = {f.name: f for f in schema_ast.functions}
        
        # Add struct fields to variables (flattened)
        for struct in schema_ast.structs:
            for field in struct.fields:
                var_name = f"{struct.name}.{field.name}"
                self._variables[var_name] = field.field_type
    
    def _tokenize(self) -> List[Token]:
        """Tokenize rule expression."""
        tokens = []
        pos = 0
        
        while pos < len(self.rule):
            # Skip whitespace
            match = WHITESPACE.match(self.rule, pos)
            if match:
                pos = match.end()
                continue
            
            # Try operators first (including multi-word)
            matched = False
            for op_str, op_enum in OPERATORS:
                if self.rule[pos:].startswith(op_str):
                    # Make sure we match whole words for word operators
                    if op_str.isalpha():
                        if (pos + len(op_str) < len(self.rule) and 
                            self.rule[pos + len(op_str)].isalnum()):
                            continue
                    tokens.append(Token(TokenType.OPERATOR, op_str, op_enum))
                    pos += len(op_str)
                    matched = True
                    break
            
            if matched:
                continue
            
            # Try other tokens
            for pattern, token_type in [
                (STRING, TokenType.STRING),
                (NUMBER, TokenType.NUMBER), 
                (NAME, TokenType.NAME),
                (LPAREN, TokenType.LPAREN),
                (RPAREN, TokenType.RPAREN),
                (COMMA, TokenType.COMMA),
                (DOT, TokenType.DOT),
            ]:
                match = pattern.match(self.rule, pos)
                if match:
                    tokens.append(Token(token_type, match.group(0)))
                    pos = match.end()
                    matched = True
                    break
            
            if not matched:
                raise RuleParseError(f"Unexpected character '{self.rule[pos]}' at position {pos}")
        
        return tokens
    
    def parse(self) -> RuleAST:
        """Parse rule into AST."""
        root = self._parse_expression()
        
        # Extract variables and functions referenced
        variables = []
        functions = []
        self._collect_references(root, variables, functions)
        
        return RuleAST(root, variables, functions)
    
    def _parse_expression(self) -> RuleNode:
        """Parse a full expression (handles OR at top level)."""
        return self._parse_or()
    
    def _parse_or(self) -> RuleNode:
        """Parse OR expressions."""
        left = self._parse_and()
        
        while self._match_operator(Operator.OR):
            operator = self._advance().operator
            right = self._parse_and()
            left = BinaryOp(operator, left, right, SchemaType.bool)
        
        return left
    
    def _parse_and(self) -> RuleNode:
        """Parse AND expressions."""
        left = self._parse_not()
        
        while self._match_operator(Operator.AND):
            operator = self._advance().operator
            right = self._parse_not()
            left = BinaryOp(operator, left, right, SchemaType.bool)
        
        return left
    
    def _parse_not(self) -> RuleNode:
        """Parse NOT expressions."""
        if self._match_operator(Operator.NOT):
            operator = self._advance().operator
            operand = self._parse_comparison()
            return UnaryOp(operator, operand, SchemaType.bool)
        
        return self._parse_comparison()
    
    def _parse_comparison(self) -> RuleNode:
        """Parse comparison expressions."""
        left = self._parse_primary()
        
        if self._match_operator(Operator.EQ, Operator.NE, Operator.GT, 
                                Operator.LT, Operator.GTE, Operator.LTE,
                                Operator.IN, Operator.NOT_IN):
            operator = self._advance().operator
            right = self._parse_primary()
            return BinaryOp(operator, left, right, SchemaType.bool)
        
        return left
    
    def _parse_primary(self) -> RuleNode:
        """Parse primary expressions."""
        token = self._peek()
        
        if not token:
            raise RuleParseError("Unexpected end of expression")
        
        if token.type == TokenType.LPAREN:
            return self._parse_parenthesized()
        elif token.type == TokenType.NUMBER:
            return self._parse_number()
        elif token.type == TokenType.STRING:
            return self._parse_string()
        elif token.type == TokenType.NAME:
            return self._parse_name_or_function()
        else:
            raise RuleParseError(f"Unexpected token: {token.value}")
    
    def _parse_parenthesized(self) -> RuleNode:
        """Parse parenthesized expression."""
        self._expect(TokenType.LPAREN)
        expr = self._parse_expression()
        self._expect(TokenType.RPAREN)
        return expr
    
    def _parse_number(self) -> RuleNode:
        """Parse number literal."""
        token = self._advance()
        value = token.value
        
        if "." in value:
            return Literal(float(value), SchemaType.float)
        else:
            return Literal(int(value), SchemaType.int)
    
    def _parse_string(self) -> RuleNode:
        """Parse string literal."""
        token = self._advance()
        # Remove quotes
        value = token.value[1:-1]
        return Literal(value, SchemaType.str)
    
    def _parse_name_or_function(self) -> RuleNode:
        """Parse variable reference or function call."""
        name_token = self._advance()
        name = name_token.value
        
        # Check if it's a function call
        if self._peek() and self._peek().type == TokenType.LPAREN:
            return self._parse_function_call(name)
        
        # Handle dotted names (struct fields)
        if self._peek() and self._peek().type == TokenType.DOT:
            return self._parse_dotted_name(name)
        
        # Regular variable
        if name in self._variables:
            return Variable(name, self._variables[name])
        
        raise RuleParseError(f"Unknown variable: {name}")
    
    def _parse_function_call(self, name: str) -> RuleNode:
        """Parse function call."""
        self._expect(TokenType.LPAREN)
        
        args = []
        while self._peek() and self._peek().type != TokenType.RPAREN:
            args.append(self._parse_expression())
            
            if self._peek() and self._peek().type == TokenType.COMMA:
                self._advance()
            elif self._peek() and self._peek().type != TokenType.RPAREN:
                raise RuleParseError("Expected ',' or ')' in function call")
        
        self._expect(TokenType.RPAREN)
        
        # Look up function return type
        if name in self._functions:
            return_type = self._functions[name].output_type
        else:
            return_type = SchemaType.any
        
        return FunctionCall(name, args, return_type)
    
    def _parse_dotted_name(self, first_part: str) -> RuleNode:
        """Parse dotted variable name (struct.field)."""
        parts = [first_part]
        
        while self._peek() and self._peek().type == TokenType.DOT:
            self._advance()  # consume dot
            if not self._peek() or self._peek().type != TokenType.NAME:
                raise RuleParseError("Expected name after '.'")
            parts.append(self._advance().value)
        
        full_name = ".".join(parts)
        
        if full_name in self._variables:
            return Variable(full_name, self._variables[full_name])
        
        raise RuleParseError(f"Unknown variable: {full_name}")
    
    def _peek(self) -> Optional[Token]:
        """Peek at current token."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def _advance(self) -> Token:
        """Consume and return current token."""
        if self.pos >= len(self.tokens):
            raise RuleParseError("Unexpected end of rule")
        token = self.tokens[self.pos]
        self.pos += 1
        return token
    
    def _expect(self, token_type: TokenType) -> Token:
        """Consume token of expected type."""
        token = self._advance()
        if token.type != token_type:
            raise RuleParseError(f"Expected {token_type.value}, got {token.type.value}")
        return token
    
    def _match_operator(self, *operators: Operator) -> bool:
        """Check if current token matches any of the given operators."""
        token = self._peek()
        return (token and token.type == TokenType.OPERATOR and 
                token.operator in operators)
    
    def _collect_references(self, node: RuleNode, variables: List[str], functions: List[str]):
        """Collect variable and function references from AST."""
        if isinstance(node, Variable):
            if node.name not in variables:
                variables.append(node.name)
        elif isinstance(node, FunctionCall):
            if node.name not in functions:
                functions.append(node.name)
            for arg in node.args:
                self._collect_references(arg, variables, functions)
        elif isinstance(node, BinaryOp):
            self._collect_references(node.left, variables, functions)
            self._collect_references(node.right, variables, functions)
        elif isinstance(node, UnaryOp):
            self._collect_references(node.operand, variables, functions)


def parse_rule(rule: str, schema_ast: SchemaAST) -> RuleAST:
    """Parse a rule expression into AST."""
    parser = RuleParser(rule, schema_ast)
    return parser.parse()