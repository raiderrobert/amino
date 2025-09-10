"""Schema parser implementation."""

import dataclasses
import enum
import re
from typing import List, Dict, Any, Optional

from ..utils.errors import SchemaParseError
from ..utils.helpers import is_reserved_name
from .types import SchemaType, parse_type
from .ast import SchemaAST, FieldDefinition, StructDefinition, FunctionDefinition


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
NUMBER = re.compile(r"\d+")
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
    
    def __init__(self, content: str):
        self.content = content
        self.tokens = self._tokenize()
        self.pos = 0
    
    def _tokenize(self) -> List[Token]:
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
                    raise SchemaParseError(f"Unexpected character '{line[pos]}' at line {line_num + 1}, column {pos + 1}")
        
        return tokens
    
    def _peek(self) -> Optional[Token]:
        """Peek at current token without consuming it."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def _advance(self) -> Optional[Token]:
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
        
        # Parse the type - should be a single WORD token for basic types
        type_token = self._expect(TokenType.WORD)
        field_type = parse_type(type_token.value)
        
        # Handle optional type (ending with ?)
        optional = False
        if self._peek() and self._peek().token_type == TokenType.QUESTION:
            optional = True
            self._advance()
        
        # Parse constraints if present
        constraints = {}
        if self._peek() and self._peek().token_type == TokenType.LBRACE:
            constraints = self._parse_constraints()
        
        return FieldDefinition(name_token.value, field_type, constraints, optional)
    
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
        
        # Parse default args if present
        default_args = []
        if self._peek() and self._peek().token_type == TokenType.LPAREN:
            self._advance()  # (
            while self._peek() and self._peek().token_type != TokenType.RPAREN:
                default_args.append(self._advance().value)
                if self._peek() and self._peek().token_type == TokenType.COMMA:
                    self._advance()
            self._expect(TokenType.RPAREN)
        
        # Parse input types
        self._expect(TokenType.LPAREN)
        input_types = []
        while self._peek() and self._peek().token_type != TokenType.RPAREN:
            type_token = self._expect(TokenType.WORD)
            input_types.append(parse_type(type_token.value))
            if self._peek() and self._peek().token_type == TokenType.COMMA:
                self._advance()
        
        self._expect(TokenType.RPAREN)
        self._expect(TokenType.ARROW)
        
        # Parse output type
        output_token = self._expect(TokenType.WORD)
        output_type = parse_type(output_token.value)
        
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
    
    def _parse_constraints(self) -> Dict[str, Any]:
        """Parse field constraints."""
        self._expect(TokenType.LBRACE)
        constraints = {}
        
        while self._peek() and self._peek().token_type != TokenType.RBRACE:
            key_token = self._expect(TokenType.WORD)
            self._expect(TokenType.COLON)
            value_token = self._advance()
            
            # Convert value based on key
            if key_token.value in ("min", "max", "length"):
                constraints[key_token.value] = int(value_token.value)
            else:
                constraints[key_token.value] = value_token.value.strip('"\'')
            
            if self._peek() and self._peek().token_type == TokenType.COMMA:
                self._advance()
        
        self._expect(TokenType.RBRACE)
        return constraints
    
    def _is_function_declaration(self) -> bool:
        """Check if current tokens represent a function declaration."""
        if self.pos + 5 >= len(self.tokens):
            return False
        
        # Look ahead for pattern: name : (type, type) -> type
        # We need to find the arrow token to distinguish from regular field
        i = self.pos + 2
        paren_count = 0
        found_arrow = False
        
        while i < len(self.tokens):
            token = self.tokens[i]
            if token.token_type == TokenType.LPAREN:
                paren_count += 1
            elif token.token_type == TokenType.RPAREN:
                paren_count -= 1
                if paren_count == 0:
                    # Check if next token is arrow
                    if i + 1 < len(self.tokens) and self.tokens[i + 1].token_type == TokenType.ARROW:
                        found_arrow = True
                    break
            i += 1
        
        return (self.tokens[self.pos].token_type == TokenType.WORD and
                self.tokens[self.pos + 1].token_type == TokenType.COLON and
                found_arrow)
    
    def _is_constant_declaration(self) -> bool:
        """Check if current tokens represent a constant declaration."""
        if self.pos + 4 >= len(self.tokens):
            return False
        
        # Look ahead for pattern: NAME : type = value
        return (self.tokens[self.pos].token_type == TokenType.WORD and
                self.tokens[self.pos].value.isupper() and
                self.tokens[self.pos + 1].token_type == TokenType.COLON and
                self.tokens[self.pos + 3].token_type == TokenType.EQUALS)


def parse_schema(content: str) -> SchemaAST:
    """Parse schema content into AST."""
    parser = SchemaParser(content)
    return parser.parse()