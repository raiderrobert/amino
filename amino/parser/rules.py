"""
Parser for the Amino rules language.
"""

from dataclasses import dataclass
import re
from typing import List, Optional, Union

from amino.types.expressions import Expression, BinaryOp, Identifier, Literal, FunctionCall


class RuleParseError(Exception):
    pass


@dataclass
class Token:
    """Represents a token in the input stream"""
    type: str
    value: str
    pos: int


class Parser:
    """Parser for the Amino rule language"""
    
    def __init__(self):
        self.tokens: List[Token] = []
        self.current: int = 0
        
        # Token definitions
        self.token_specs = [
            ('NUMBER', r'\d+(_\d+)*'),
            ('STRING', r"'[^']*'|\"[^\"]*\""),
            ('AND', r'and\b'),
            ('OR', r'or\b'),
            ('IN', r'in\b'),
            ('NOT_IN', r'not\s+in\b'),
            ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('COMPARISON', r'>=|<=|!=|=|>|<'),
            ('LPAREN', r'\('),
            ('RPAREN', r'\)'),
            ('DOT', r'\.'),
            ('COMMA', r','),
            ('WHITESPACE', r'\s+'),
        ]
        
        # Combine all patterns
        self.pattern = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.token_specs)
        self.regex = re.compile(self.pattern)

    def tokenize(self, text: str) -> List[Token]:
        """Convert input text into a list of tokens"""
        tokens = []
        pos = 0
        
        while pos < len(text):
            match = self.regex.match(text, pos)
            if match is None:
                raise RuleParseError(f"Invalid character at position {pos}")
            
            token_type = match.lastgroup
            token_value = match.group()
            
            if token_type != 'WHITESPACE':
                # Clean up literals
                if token_type == 'STRING':
                    token_value = token_value[1:-1]  # Remove quotes
                elif token_type == 'NUMBER':
                    token_value = token_value.replace('_', '')  # Remove digit separators
                
                tokens.append(Token(token_type, token_value, pos))
            
            pos = match.end()
        
        self.tokens = tokens
        self.current = 0
        return tokens

    def parse(self, text: str) -> Expression:
        """Parse input text into an Expression"""
        self.tokenize(text)
        return self.parse_logical()

    def parse_logical(self) -> Expression:
        """Parse logical expressions (and/or)"""
        expr = self.parse_comparison()
        
        while self.check('AND') or self.check('OR'):
            operator = self.advance().value
            right = self.parse_comparison()
            expr = BinaryOp(expr, operator, right)
        
        return expr

    def parse_comparison(self) -> Expression:
        """Parse comparison expressions"""
        expr = self.parse_membership()
        
        if self.check('COMPARISON'):
            operator = self.advance().value
            right = self.parse_membership()
            expr = BinaryOp(expr, operator, right)
        
        return expr

    def parse_membership(self) -> Expression:
        """Parse membership expressions (in/not in)"""
        expr = self.parse_primary()
        
        if self.check('IN'):
            operator = self.advance().value
            right = self.parse_primary()
            expr = BinaryOp(expr, operator, right)
        elif self.check('NOT_IN'):
            operator = self.advance().value
            right = self.parse_primary()
            expr = BinaryOp(expr, operator, right)
        
        return expr

    def parse_primary(self) -> Expression:
        """Parse primary expressions"""
        if self.check('NUMBER'):
            return Literal(int(self.advance().value))
        
        if self.check('STRING'):
            return Literal(self.advance().value)
        
        if self.check('IDENTIFIER'):
            identifier = self.advance().value
            
            # Function call
            if self.check('LPAREN'):
                self.advance()  # consume (
                args = []
                if not self.check('RPAREN'):
                    args.append(self.parse_logical())
                    while self.check('COMMA'):
                        self.advance()  # consume ,
                        args.append(self.parse_logical())
                
                self.consume('RPAREN', "Expect ')' after arguments")
                return FunctionCall(identifier, args)
            
            # Nested identifier
            if self.check('DOT'):
                self.advance()  # consume .
                self.consume('IDENTIFIER', "Expect identifier after '.'")
                nested = self.previous().value
                return Identifier(f"{identifier}.{nested}")
            
            return Identifier(identifier)
        
        if self.check('LPAREN'):
            self.advance()  # consume (
            expr = self.parse_logical()
            self.consume('RPAREN', "Expect ')' after expression")
            return expr
        
        if self.is_at_end():
            raise RuleParseError("Unexpected end of input")
        
        raise RuleParseError(f"Unexpected token: {self.peek().value}")

    def check(self, type_: str) -> bool:
        """Check if current token is of given type"""
        if self.is_at_end():
            return False
        return self.peek().type == type_

    def advance(self) -> Token:
        """Advance to next token"""
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def consume(self, type_: str, message: str) -> Token:
        """Consume a token of the expected type or raise error"""
        if self.check(type_):
            return self.advance()
        if self.is_at_end():
            raise RuleParseError(f"{message} at end of input")
        raise RuleParseError(f"{message} at {self.peek().value}")

    def is_at_end(self) -> bool:
        """Check if we've reached end of tokens"""
        return self.current >= len(self.tokens)

    def peek(self) -> Token:
        """Look at current token"""
        if self.is_at_end():
            raise RuleParseError("Unexpected end of input")
        return self.tokens[self.current]

    def previous(self) -> Token:
        """Get previous token"""
        return self.tokens[self.current - 1]


def parse_rule(text: str) -> Expression:
    """Parse a rule from text"""
    parser = Parser()
    return parser.parse(text)