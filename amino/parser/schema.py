"""
Parser for the Amino schema language.
"""

from dataclasses import dataclass
import re
from typing import List, Dict, Optional

from amino.types.base import Type, PrimitiveType, ListType, StructType, FunctionType, TypeKind


class SchemaParseError(Exception):
    pass


@dataclass
class SchemaToken:
    type: str
    value: str
    pos: int


class SchemaParser:
    """Parser for Amino schema files"""
    
    def __init__(self):
        self.tokens: List[SchemaToken] = []
        self.current: int = 0
        
        # Token definitions - order matters!
        self.token_specs = [
            ('WHITESPACE', r'[ \t]+'),
            ('NEWLINE', r'[\r\n]+'),
            ('COMMENT', r'#[^\r\n]*'),
            ('STRUCT', r'struct\b'),
            ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),  # This must come before TYPE
            ('TYPE', r'int|str|float|bool|list'),
            ('EQUALS', r'='),
            ('COMMA', r','),
            ('COLON', r':'),
            ('LBRACE', r'\{'),
            ('RBRACE', r'\}'),
            ('LBRACKET', r'\['),
            ('RBRACKET', r'\]'),
            ('LPAREN', r'\('),
            ('RPAREN', r'\)'),
            ('ARROW', r'->'),
            ('NUMBER', r'\d+(_\d+)*'),
            ('STRING', r"'[^']*'|\"[^\"]*\""),
        ]
        
        # Combine all patterns
        self.pattern = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.token_specs)
        self.regex = re.compile(self.pattern)

    def tokenize(self, text: str) -> List[SchemaToken]:
        """Convert schema text into tokens"""
        tokens = []
        pos = 0
        line_num = 1
        line_start = 0
        
        while pos < len(text):
            match = self.regex.match(text, pos)
            if match is None:
                # Skip any remaining whitespace
                while pos < len(text) and text[pos].isspace():
                    if text[pos] in '\r\n':
                        line_num += 1
                        line_start = pos + 1
                    pos += 1
                if pos < len(text):
                    raise SchemaParseError(f"Invalid character at line {line_num}, position {pos - line_start + 1}: '{text[pos]}'")
                break
            
            token_type = match.lastgroup
            token_value = match.group()
            
            if token_type == 'NEWLINE':
                line_num += token_value.count('\n')
                line_start = pos + len(token_value)
            elif token_type not in {'WHITESPACE', 'COMMENT'}:
                if token_type == 'STRING':
                    token_value = token_value[1:-1]  # Remove quotes
                elif token_type == 'NUMBER':
                    token_value = token_value.replace('_', '')
                
                tokens.append(SchemaToken(token_type, token_value, pos))
            
            pos = match.end()
        
        self.tokens = tokens
        self.current = 0
        return self.tokens

    def parse(self, text: str) -> Dict[str, Type]:
        """Parse schema text into type definitions"""
        self.tokenize(text)
        types = {}
        
        while not self.is_at_end():
            # Skip any extra newlines
            while self.match('NEWLINE'):
                continue
            
            if self.is_at_end():
                break
            
            # Parse struct definition
            if self.match('STRUCT'):
                name = self.consume('IDENTIFIER', "Expect struct name")
                self.consume('LBRACE', "Expect '{' after struct name")
                
                fields = {}
                while not self.check('RBRACE') and not self.is_at_end():
                    field_name = self.consume('IDENTIFIER', "Expect field name").value
                    self.consume('COLON', "Expect ':' after field name")
                    field_type = self.parse_type()
                    fields[field_name] = field_type
                    
                    # Handle optional comma
                    self.match('COMMA')
                    
                    # Skip newlines between fields
                    while self.match('NEWLINE'):
                        continue
                
                self.consume('RBRACE', "Expect '}' after struct fields")
                types[name.value] = StructType(name.value, fields)
            
            # Parse variable definition
            elif self.check('IDENTIFIER'):
                name = self.advance()  # consume identifier
                self.consume('COLON', "Expect ':' after variable name")
                var_type = self.parse_type()
                
                # Check for default value
                if self.match('EQUALS'):
                    # Skip default value for now
                    while not self.is_at_end() and not self.check('NEWLINE'):
                        self.advance()
                
                types[name.value] = var_type
            
            else:
                raise SchemaParseError(f"Expected struct or variable declaration, got {self.peek().type}")
        
        return types

    def parse_type(self) -> Type:
        """Parse a type expression"""
        # Handle basic types
        if self.check('IDENTIFIER'):
            type_name = self.peek().value
            if type_name in {'int', 'str', 'float', 'bool', 'list'}:
                self.advance()  # consume type
                if type_name == 'list':
                    self.consume('LBRACKET', "Expect '[' after 'list'")
                    element_type = self.parse_type()
                    self.consume('RBRACKET', "Expect ']' after element type")
                    return ListType(element_type)
                else:
                    return PrimitiveType(getattr(TypeKind, type_name.upper()))
        
        raise SchemaParseError(f"Expected type but got '{self.peek().value}'")

    def match(self, type_: str) -> bool:
        """Check if current token matches type"""
        if self.check(type_):
            self.advance()
            return True
        return False

    def check(self, type_: str) -> bool:
        """Check if current token is of given type"""
        if self.is_at_end():
            return False
        return self.peek().type == type_

    def advance(self) -> SchemaToken:
        """Advance to next token"""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def consume(self, type_: str, message: str) -> SchemaToken:
        """Consume a token of the expected type or raise error"""
        if self.check(type_):
            return self.advance()
        if self.is_at_end():
            raise SchemaParseError(f"{message} at end of input")
        raise SchemaParseError(f"{message}, got '{self.peek().value}'")

    def is_at_end(self) -> bool:
        """Check if we've reached end of tokens"""
        return self.current >= len(self.tokens)

    def peek(self) -> SchemaToken:
        """Look at current token"""
        if self.is_at_end():
            raise SchemaParseError("Unexpected end of input")
        return self.tokens[self.current]

    def previous(self) -> SchemaToken:
        """Get previous token"""
        return self.tokens[self.current - 1]


def parse_schema(text: str) -> Dict[str, Type]:
    """Parse a schema from text"""
    parser = SchemaParser()
    return parser.parse(text)