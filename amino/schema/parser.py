"""Schema parser implementation."""

import dataclasses
import enum
import re
from typing import Any

from ..utils.errors import SchemaParseError
from ..utils.helpers import is_reserved_name
from .ast import FieldDefinition, FunctionDefinition, SchemaAST, StructDefinition
from .types import SchemaType, parse_type

# Token patterns
WHITESPACE = re.compile(r"[\s]+")
WORD = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
COLON = re.compile(r":")
COMMA = re.compile(r",")
EQUALS = re.compile(r"=")
LBRACE = re.compile(r"\{")
RBRACE = re.compile(r"\}")
LPAREN = re.compile(r"\(")
RPAREN = re.compile(r"\)")
ARROW = re.compile(r"->")
PIPE = re.compile(r"\|")
LBRACKET = re.compile(r"\[")
RBRACKET = re.compile(r"\]")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
QUESTION = re.compile(r"\?")
COMMENT = re.compile(r"#[^\n]*")


class TokenType(enum.Enum):
    """Token types for schema parsing."""
    WHITESPACE = "whitespace"
    WORD = "word"
    COLON = "colon"
    COMMA = "comma"
    EQUALS = "equals"
    LBRACE = "lbrace"
    RBRACE = "rbrace"
    LPAREN = "lparen"
    RPAREN = "rparen"
    ARROW = "arrow"
    PIPE = "pipe"
    LBRACKET = "lbracket"
    RBRACKET = "rbracket"
    NUMBER = "number"
    QUESTION = "question"
    COMMENT = "comment"


TOKEN_PATTERNS = [
    (COMMENT, TokenType.COMMENT),
    (ARROW, TokenType.ARROW),
    (WHITESPACE, TokenType.WHITESPACE),
    (WORD, TokenType.WORD),
    (COLON, TokenType.COLON),
    (COMMA, TokenType.COMMA),
    (EQUALS, TokenType.EQUALS),
    (LBRACE, TokenType.LBRACE),
    (RBRACE, TokenType.RBRACE),
    (LPAREN, TokenType.LPAREN),
    (RPAREN, TokenType.RPAREN),
    (PIPE, TokenType.PIPE),
    (LBRACKET, TokenType.LBRACKET),
    (RBRACKET, TokenType.RBRACKET),
    (NUMBER, TokenType.NUMBER),
    (QUESTION, TokenType.QUESTION),
]


@dataclasses.dataclass
class Token:
    """Schema token."""
    value: str
    token_type: TokenType
    line: int = 0
    column: int = 0


class SchemaParser:
    """Parser for schema definition language."""

    def __init__(self, content: str, strict: bool = False,
                 known_custom_types: set | None = None):
        self.content = content
        self.strict = strict
        self.known_custom_types = known_custom_types or set()
        self.tokens = self._tokenize()
        self.pos = 0

    def _tokenize(self) -> list[Token]:
        """Tokenize schema content."""
        tokens = []
        lines = self.content.split('\n')

        for line_num, line in enumerate(lines):
            pos = 0
            while pos < len(line):
                matched = False
                for pattern, token_type in TOKEN_PATTERNS:
                    match = pattern.match(line, pos)
                    if match:
                        value = match.group(0)
                        if token_type not in (TokenType.WHITESPACE, TokenType.COMMENT):
                            tokens.append(Token(value, token_type, line_num + 1, pos))
                        pos = match.end()
                        matched = True
                        break

                if not matched:
                    raise SchemaParseError(
                        f"Unexpected character '{line[pos]}' at line {line_num + 1}, column {pos + 1}"
                    )

        return tokens

    def _peek(self) -> Token | None:
        """Peek at current token without consuming it."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self) -> Token | None:
        """Consume and return current token."""
        if self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            self.pos += 1
            return token
        return None

    def _expect(self, token_type: TokenType) -> Token:
        """Consume token of expected type or raise error."""
        token = self._advance()
        if not token or token.token_type != token_type:
            expected = token_type.value
            actual = token.token_type.value if token else "EOF"
            raise SchemaParseError(f"Expected {expected}, got {actual}")
        return token

    def parse(self) -> SchemaAST:
        """Parse schema content into AST."""
        ast = SchemaAST()

        while self._peek():
            token = self._peek()

            if token.value == "struct":
                ast.structs.append(self._parse_struct())
            elif self._is_function_declaration():
                ast.functions.append(self._parse_function())
            elif self._is_constant_declaration():
                name, value = self._parse_constant()
                ast.constants[name] = value
            else:
                ast.fields.append(self._parse_field())

        return ast

    def _parse_field(self) -> FieldDefinition:
        """Parse a field definition."""
        name_token = self._expect(TokenType.WORD)
        if is_reserved_name(name_token.value):
            raise SchemaParseError(f"Cannot use reserved name: {name_token.value}")

        self._expect(TokenType.COLON)

        # Parse the type - can be simple (int) or complex (list[str])
        type_info = self._parse_type_expression()
        field_type = type_info["type"]
        type_name = type_info["name"]
        element_types = type_info.get("element_types", [])

        # Handle optional type (ending with ?)
        optional = False
        if self._peek() and self._peek().token_type == TokenType.QUESTION:
            optional = True
            self._advance()

        # Parse constraints if present
        constraints = {}
        if self._peek() and self._peek().token_type == TokenType.LBRACE:
            constraints = self._parse_constraints()

        return FieldDefinition(name_token.value, field_type, type_name, element_types, constraints, optional)

    def _parse_struct(self) -> StructDefinition:
        """Parse a struct definition."""
        self._expect(TokenType.WORD)  # 'struct'
        name_token = self._expect(TokenType.WORD)
        self._expect(TokenType.LBRACE)

        fields = []
        while self._peek() and self._peek().token_type != TokenType.RBRACE:
            fields.append(self._parse_field())
            if self._peek() and self._peek().token_type == TokenType.COMMA:
                self._advance()

        self._expect(TokenType.RBRACE)
        return StructDefinition(name_token.value, fields)

    def _parse_function(self) -> FunctionDefinition:
        """Parse a function declaration."""
        name_token = self._expect(TokenType.WORD)
        self._expect(TokenType.COLON)

        # Parse default args if present (pattern: (DEFAULT_ARGS)(input_types) -> output)
        default_args = []

        # Check if we have default args by looking ahead
        # Default args: (NAME)(types) -> type
        # Input types: (type, type) -> type
        # The key difference: default args are followed by another ( for input types
        if (self._peek() and self._peek().token_type == TokenType.LPAREN and
            self.pos + 3 < len(self.tokens) and
            self.tokens[self.pos + 1].token_type == TokenType.WORD and
            self.tokens[self.pos + 2].token_type == TokenType.RPAREN and
            self.tokens[self.pos + 3].token_type == TokenType.LPAREN):
            # This is default args: (NAME) followed by another (
            self._advance()  # consume (
            while self._peek() and self._peek().token_type != TokenType.RPAREN:
                default_args.append(self._advance().value)
                if self._peek() and self._peek().token_type == TokenType.COMMA:
                    self._advance()
            self._expect(TokenType.RPAREN)

        # Parse input types - now expect the input types parentheses
        self._expect(TokenType.LPAREN)
        input_types = []
        while self._peek() and self._peek().token_type != TokenType.RPAREN:
            type_token = self._expect(TokenType.WORD)
            input_types.append(parse_type(type_token.value, self.strict, self.known_custom_types))
            if self._peek() and self._peek().token_type == TokenType.COMMA:
                self._advance()

        self._expect(TokenType.RPAREN)
        self._expect(TokenType.ARROW)

        # Parse output type
        output_token = self._expect(TokenType.WORD)
        output_type = parse_type(output_token.value, self.strict, self.known_custom_types)

        return FunctionDefinition(name_token.value, input_types, output_type, default_args)

    def _parse_constant(self) -> tuple[str, Any]:
        """Parse a constant declaration."""
        name_token = self._expect(TokenType.WORD)
        self._expect(TokenType.COLON)
        type_token = self._expect(TokenType.WORD)
        self._expect(TokenType.EQUALS)
        value_token = self._expect(TokenType.NUMBER)

        # Convert value based on type
        if type_token.value == "int":
            value = int(value_token.value)
        elif type_token.value == "float":
            value = float(value_token.value)
        else:
            value = value_token.value

        return name_token.value, value

    def _parse_constraints(self) -> dict[str, Any]:
        """Parse field constraints."""
        self._expect(TokenType.LBRACE)
        constraints = {}

        while self._peek() and self._peek().token_type != TokenType.RBRACE:
            key_token = self._expect(TokenType.WORD)
            self._expect(TokenType.COLON)
            value_token = self._advance()

            # Convert value based on key and type
            if key_token.value in ("min", "max", "length"):
                # Try to convert to int first, then float if it contains a decimal point
                if "." in value_token.value:
                    constraints[key_token.value] = float(value_token.value)
                else:
                    constraints[key_token.value] = int(value_token.value)
            else:
                constraints[key_token.value] = value_token.value.strip('"\'')

            if self._peek() and self._peek().token_type == TokenType.COMMA:
                self._advance()

        self._expect(TokenType.RBRACE)
        return constraints

    def _parse_type_expression(self) -> dict[str, Any]:
        """Parse a type expression (simple or complex like list[type])."""
        type_token = self._expect(TokenType.WORD)
        type_name = type_token.value

        # Check if this is a list type with element specification
        if type_name == "list" and self._peek() and self._peek().token_type == TokenType.LBRACKET:
            self._advance()  # consume '['

            # Parse element types (can be type1|type2|type3)
            element_types = []
            while self._peek() and self._peek().token_type != TokenType.RBRACKET:
                elem_token = self._expect(TokenType.WORD)
                element_types.append(elem_token.value)

                # Check for union type separator '|'
                if self._peek() and self._peek().token_type == TokenType.PIPE:
                    self._advance()  # consume '|'
                elif self._peek() and self._peek().token_type != TokenType.RBRACKET:
                    raise SchemaParseError("Expected '|' or ']' in list type definition")

            self._expect(TokenType.RBRACKET)  # consume ']'

            return {
                "type": SchemaType.list,
                "name": f"list[{'|'.join(element_types)}]",
                "element_types": element_types
            }
        else:
            # Simple type
            field_type = parse_type(type_name, self.strict, self.known_custom_types)
            return {
                "type": field_type,
                "name": type_name,
                "element_types": []
            }

    def _is_function_declaration(self) -> bool:
        """Check if current tokens represent a function declaration."""
        if self.pos + 3 >= len(self.tokens):
            return False

        # Check basic pattern: name : ...
        if not (self.tokens[self.pos].token_type == TokenType.WORD and
                self.tokens[self.pos + 1].token_type == TokenType.COLON):
            return False

        # Look ahead for pattern: name : (type, type) -> type
        # Start looking after the colon
        i = self.pos + 2
        paren_count = 0
        found_arrow = False

        # Only look ahead a reasonable distance (max 20 tokens to avoid false positives)
        max_lookahead = min(i + 20, len(self.tokens))

        while i < max_lookahead:
            token = self.tokens[i]
            if token.token_type == TokenType.LPAREN:
                paren_count += 1
            elif token.token_type == TokenType.RPAREN:
                paren_count -= 1
                # Only stop if we've found an arrow after closing all parentheses
                if paren_count == 0:
                    # Check if next token is arrow
                    if i + 1 < len(self.tokens) and self.tokens[i + 1].token_type == TokenType.ARROW:
                        found_arrow = True
                        break
            elif token.token_type == TokenType.WORD and paren_count == 0:
                # If we hit another word at paren_count 0, this is likely the next declaration
                break
            i += 1

        return found_arrow

    def _is_constant_declaration(self) -> bool:
        """Check if current tokens represent a constant declaration."""
        if self.pos + 4 >= len(self.tokens):
            return False

        # Look ahead for pattern: NAME : type = value
        return (self.tokens[self.pos].token_type == TokenType.WORD and
                self.tokens[self.pos].value.isupper() and
                self.tokens[self.pos + 1].token_type == TokenType.COLON and
                self.tokens[self.pos + 3].token_type == TokenType.EQUALS)


def parse_schema(content: str, strict: bool = False,
                known_custom_types: set | None = None) -> SchemaAST:
    """Parse schema content into AST.

    Args:
        content: Schema content to parse
        strict: If True, raise error for unknown types instead of treating as custom
        known_custom_types: Set of known custom type names for validation
    """
    parser = SchemaParser(content, strict=strict,
                         known_custom_types=known_custom_types)
    return parser.parse()
