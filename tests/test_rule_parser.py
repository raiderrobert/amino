"""
Tests for the rule parser.
"""

import pytest
from amino.parser.rules import parse_rule, RuleParseError
from amino.types.expressions import BinaryOp, Identifier, Literal, FunctionCall


def test_basic_comparison():
    """Test parsing of basic comparison expressions"""
    expr = parse_rule("amount > 0")
    assert isinstance(expr, BinaryOp)
    assert expr.op == ">"
    assert isinstance(expr.left, Identifier)
    assert expr.left.name == "amount"
    assert isinstance(expr.right, Literal)
    assert expr.right.value == 0

def test_string_comparison():
    """Test parsing of string comparisons"""
    expr = parse_rule("state_code = 'CA'")
    assert isinstance(expr, BinaryOp)
    assert expr.op == "="
    assert isinstance(expr.left, Identifier)
    assert expr.left.name == "state_code"
    assert isinstance(expr.right, Literal)
    assert expr.right.value == "CA"

def test_logical_operators():
    """Test parsing of logical operators"""
    expr = parse_rule("amount > 0 and state_code = 'CA'")
    assert isinstance(expr, BinaryOp)
    assert expr.op == "and"
    
    # Check left side (amount > 0)
    assert isinstance(expr.left, BinaryOp)
    assert expr.left.op == ">"
    assert isinstance(expr.left.left, Identifier)
    assert expr.left.left.name == "amount"
    assert isinstance(expr.left.right, Literal)
    assert expr.left.right.value == 0
    
    # Check right side (state_code = 'CA')
    assert isinstance(expr.right, BinaryOp)
    assert expr.right.op == "="
    assert isinstance(expr.right.left, Identifier)
    assert expr.right.left.name == "state_code"
    assert isinstance(expr.right.right, Literal)
    assert expr.right.right.value == "CA"

def test_nested_identifiers():
    """Test parsing of nested identifier access"""
    expr = parse_rule("user.age >= 18")
    assert isinstance(expr, BinaryOp)
    assert expr.op == ">="
    assert isinstance(expr.left, Identifier)
    assert expr.left.name == "user.age"
    assert isinstance(expr.right, Literal)
    assert expr.right.value == 18

def test_list_membership():
    """Test parsing of list membership operations"""
    # Test 'in' operator
    expr = parse_rule("100 in scores")
    assert isinstance(expr, BinaryOp)
    assert expr.op == "in"
    assert isinstance(expr.left, Literal)
    assert expr.left.value == 100
    assert isinstance(expr.right, Identifier)
    assert expr.right.name == "scores"
    
    # Test 'not in' operator
    expr = parse_rule("'NY' not in allowed_states")
    assert isinstance(expr, BinaryOp)
    assert expr.op == "not in"
    assert isinstance(expr.left, Literal)
    assert expr.left.value == "NY"
    assert isinstance(expr.right, Identifier)
    assert expr.right.name == "allowed_states"

def test_function_calls():
    """Test parsing of function calls"""
    expr = parse_rule("min(amount, 1000)")
    assert isinstance(expr, FunctionCall)
    assert expr.name == "min"
    assert len(expr.args) == 2
    assert isinstance(expr.args[0], Identifier)
    assert expr.args[0].name == "amount"
    assert isinstance(expr.args[1], Literal)
    assert expr.args[1].value == 1000

def test_complex_expression():
    """Test parsing of complex expressions"""
    expr = parse_rule("user.age >= 18 and (score > 90 or role = 'admin')")
    assert isinstance(expr, BinaryOp)
    assert expr.op == "and"
    
    # Check age comparison
    assert isinstance(expr.left, BinaryOp)
    assert expr.left.op == ">="
    assert isinstance(expr.left.left, Identifier)
    assert expr.left.left.name == "user.age"
    assert isinstance(expr.left.right, Literal)
    assert expr.left.right.value == 18
    
    # Check right side (score > 90 or role = 'admin')
    assert isinstance(expr.right, BinaryOp)
    assert expr.right.op == "or"
    
    # Check score comparison
    assert isinstance(expr.right.left, BinaryOp)
    assert expr.right.left.op == ">"
    assert isinstance(expr.right.left.left, Identifier)
    assert expr.right.left.left.name == "score"
    assert isinstance(expr.right.left.right, Literal)
    assert expr.right.left.right.value == 90
    
    # Check role comparison
    assert isinstance(expr.right.right, BinaryOp)
    assert expr.right.right.op == "="
    assert isinstance(expr.right.right.left, Identifier)
    assert expr.right.right.left.name == "role"
    assert isinstance(expr.right.right.right, Literal)
    assert expr.right.right.right.value == "admin"

def test_invalid_syntax():
    """Test handling of invalid syntax"""
    with pytest.raises(RuleParseError):
        parse_rule("amount > ")  # Incomplete expression
    
    with pytest.raises(RuleParseError):
        parse_rule("amount >>= 0")  # Invalid operator
    
    with pytest.raises(RuleParseError):
        parse_rule("and amount > 0")  # Starting with operator