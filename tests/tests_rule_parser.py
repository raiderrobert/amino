import pytest
from amino.rules.parser import parse_rule
from amino.rules.ast import BinaryOp, Literal, Variable, Operator
from amino.schema.parser import parse_schema
from amino.utils.errors import RuleParseError


@pytest.mark.parametrize(
    "schema_content,rule,should_raise,expected_error",
    [
        (
            "a: int\nb: int",
            "a > 1",
            False,
            None,
        ),
        (
            "a: int\nb: int", 
            "2 > 1",
            False,
            None,
        ),
        (
            "a: int\nb: int",
            "a > b and b > 0",
            False,
            None,
        ),
        (
            "name: str\nage: int",
            "name = 'John' and age >= 18",
            False,
            None,
        ),
        (
            "amount: int",
            "amount > unknown_var",
            True,
            "Unknown variable: unknown_var",
        ),
        (
            "amount: int",
            "amount > 0 and",
            True,
            "Unexpected end of rule",
        ),
    ],
)
def test_rule_parsing(schema_content, rule, should_raise, expected_error):
    """Test rule parsing with new architecture."""
    schema_ast = parse_schema(schema_content)
    
    if should_raise:
        with pytest.raises(RuleParseError) as excinfo:
            parse_rule(rule, schema_ast)
        assert expected_error in str(excinfo.value)
    else:
        rule_ast = parse_rule(rule, schema_ast)
        assert rule_ast.root is not None
        assert hasattr(rule_ast, 'variables')
        assert hasattr(rule_ast, 'functions')


def test_simple_comparison():
    """Test parsing simple comparison."""
    schema_ast = parse_schema("amount: int")
    rule_ast = parse_rule("amount > 100", schema_ast)
    
    assert isinstance(rule_ast.root, BinaryOp)
    assert rule_ast.root.operator == Operator.GT
    assert isinstance(rule_ast.root.left, Variable)
    assert rule_ast.root.left.name == "amount"
    assert isinstance(rule_ast.root.right, Literal)
    assert rule_ast.root.right.value == 100


def test_literal_comparison():
    """Test parsing literal comparison."""
    schema_ast = parse_schema("amount: int")
    rule_ast = parse_rule("100 > 50", schema_ast)
    
    assert isinstance(rule_ast.root, BinaryOp)
    assert rule_ast.root.operator == Operator.GT
    assert isinstance(rule_ast.root.left, Literal)
    assert rule_ast.root.left.value == 100
    assert isinstance(rule_ast.root.right, Literal)
    assert rule_ast.root.right.value == 50


def test_logical_and():
    """Test parsing logical AND."""
    schema_ast = parse_schema("amount: int\nstate: str")
    rule_ast = parse_rule("amount > 0 and state = 'CA'", schema_ast)
    
    assert isinstance(rule_ast.root, BinaryOp)
    assert rule_ast.root.operator == Operator.AND
    assert isinstance(rule_ast.root.left, BinaryOp)
    assert isinstance(rule_ast.root.right, BinaryOp)
    
    # Check variables are collected
    assert "amount" in rule_ast.variables
    assert "state" in rule_ast.variables


def test_string_literals():
    """Test parsing string literals with quotes."""
    schema_ast = parse_schema("name: str")
    
    # Single quotes
    rule_ast = parse_rule("name = 'John'", schema_ast)
    assert isinstance(rule_ast.root.right, Literal)
    assert rule_ast.root.right.value == "John"
    
    # Double quotes  
    rule_ast = parse_rule('name = "Jane"', schema_ast)
    assert isinstance(rule_ast.root.right, Literal)
    assert rule_ast.root.right.value == "Jane"


def test_parentheses():
    """Test parsing expressions with parentheses."""
    schema_ast = parse_schema("a: int\nb: int\nc: int")
    rule_ast = parse_rule("(a > 0 and b > 0) or c > 0", schema_ast)
    
    assert isinstance(rule_ast.root, BinaryOp)
    assert rule_ast.root.operator == Operator.OR


def test_function_calls():
    """Test parsing function calls."""
    schema_ast = parse_schema("amount: int\nmax_amount: int\nmin_func: (int, int) -> int")
    rule_ast = parse_rule("min_func(amount, max_amount) > 0", schema_ast)
    
    assert isinstance(rule_ast.root, BinaryOp)
    assert "min_func" in rule_ast.functions


def test_struct_field_access():
    """Test parsing struct field access."""
    schema_ast = parse_schema("""
    struct person {
        name: str,
        age: int
    }
    """)
    rule_ast = parse_rule("person.age > 18", schema_ast)
    
    assert isinstance(rule_ast.root.left, Variable)
    assert rule_ast.root.left.name == "person.age"
