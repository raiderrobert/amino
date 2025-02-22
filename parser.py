from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import re
from type_system import Expression, BinaryOp, Identifier, Literal, FunctionCall

class ParseError(Exception):
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
            ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
            ('OPERATOR', r'(>=|<=|!=|=|>|<|and|or|in|not\s+in)'),
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
                raise ParseError(f"Invalid character at position {pos}")
            
            token_type = match.lastgroup
            token_value = match.group()
            
            if token_type != 'WHITESPACE':
                # Clean up string literals
                if token_type == 'STRING':
                    token_value = token_value[1:-1]  # Remove quotes
                elif token_type == 'NUMBER':
                    token_value = token_value.replace('_', '')  # Remove underscores
                
                tokens.append(Token(token_type, token_value, pos))
            
            pos = match.end()
        
        self.tokens = tokens
        self.current = 0
        return tokens

    def parse(self, text: str) -> Expression:
        """Parse input text into an Expression"""
        self.tokenize(text)
        return self.parse_expression()

    def parse_expression(self) -> Expression:
        """Parse a full expression"""
        expr = self.parse_comparison()
        
        while self.match('OPERATOR', {'and', 'or'}):
            operator = self.previous().value
            right = self.parse_comparison()
            expr = BinaryOp(expr, operator, right)
        
        return expr

    def parse_comparison(self) -> Expression:
        """Parse a comparison expression"""
        expr = self.parse_primary()
        
        while self.match('OPERATOR', {'=', '!=', '>', '<', '>=', '<=', 'in', 'not in'}):
            operator = self.previous().value
            right = self.parse_primary()
            expr = BinaryOp(expr, operator, right)
        
        return expr

    def parse_primary(self) -> Expression:
        """Parse a primary expression (literal, identifier, or grouped expression)"""
        if self.match('NUMBER'):
            return Literal(int(self.previous().value))
        
        if self.match('STRING'):
            return Literal(self.previous().value)
        
        if self.match('IDENTIFIER'):
            identifier = self.previous().value
            
            # Check for function call
            if self.match('LPAREN'):
                args = []
                if not self.check('RPAREN'):
                    args.append(self.parse_expression())
                    while self.match('COMMA'):
                        args.append(self.parse_expression())
                
                self.consume('RPAREN', "Expect ')' after arguments")
                return FunctionCall(identifier, args)
            
            # Check for nested identifier
            if self.match('DOT'):
                self.consume('IDENTIFIER', "Expect identifier after '.'")
                nested = self.previous().value
                return Identifier(f"{identifier}.{nested}")
            
            return Identifier(identifier)
        
        if self.match('LPAREN'):
            expr = self.parse_expression()
            self.consume('RPAREN', "Expect ')' after expression")
            return expr
        
        raise ParseError(f"Unexpected token: {self.peek().value}")

    def match(self, type_: str, values: Optional[set] = None) -> bool:
        """Check if current token matches type and optional values"""
        if self.is_at_end():
            return False
        
        token = self.peek()
        if token.type != type_:
            return False
        
        if values is not None and token.value not in values:
            return False
        
        self.current += 1
        return True

    def consume(self, type_: str, message: str) -> Token:
        """Consume a token of the expected type or raise error"""
        if self.check(type_):
            return self.advance()
        raise ParseError(f"{message} at {self.peek().pos}")

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

    def is_at_end(self) -> bool:
        """Check if we've reached end of tokens"""
        return self.current >= len(self.tokens)

    def peek(self) -> Token:
        """Look at current token"""
        return self.tokens[self.current]

    def previous(self) -> Token:
        """Get previous token"""
        return self.tokens[self.current - 1]


# Update RuleEngine to use the parser
class RuleEngine:
    """Main rule engine that evaluates rules against datasets"""
    
    def __init__(self, type_checker: TypeChecker):
        self.type_checker = type_checker
        self.evaluator = Evaluator(type_checker)
        self.parser = Parser()
        self.rules: List[Rule] = []
        self.match_config: Optional[RuleMatch] = None

    def _parse_expression(self, rule_str: str) -> Expression:
        """Parse a rule string into an Expression"""
        return self.parser.parse(rule_str)


# ---- Example Usage ----

def example_usage():
    from type_system import PrimitiveType, TypeChecker
    
    # Create type system
    schema_types = {
        'amount': PrimitiveType.INT(),
        'state_code': PrimitiveType.STR(),
        'bool': PrimitiveType.BOOL(),
    }
    
    type_checker = TypeChecker(schema_types)
    
    # Create rule engine
    engine = RuleEngine(type_checker)
    
    # Add rules using string syntax
    rules = [
        {
            'id': 1,
            'rule': "amount > 0 and state_code = 'CA'",
        },
        {
            'id': 2,
            'rule': "amount >= 100",
        }
    ]
    
    # Add rules to engine
    engine.add_rules(rules)
    
    # Example datasets
    datasets = [
        {'id': 45, 'amount': 100, 'state_code': 'CA'},
        {'id': 46, 'amount': 50, 'state_code': 'CA'},
        {'id': 47, 'amount': 100, 'state_code': 'NY'},
    ]
    
    # Evaluate rules
    results = engine.evaluate(datasets)
    print(results)

if __name__ == '__main__':
    example_usage()