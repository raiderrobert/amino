import pytest

from amino.rules.ast import BinaryOp, Literal, Operator, Variable
from amino.rules.parser import parse_rule
from amino.schema.parser import parse_schema
from amino.utils.errors import RuleParseError


@pytest.mark.parametrize(
    "schema_content,rule,should_raise,expected_error",
    [
        (
            "a: Int\nb: Int",
            "a > 1",
            False,
            None,
        ),
        (
            "a: Int\nb: Int",
            "2 > 1",
            False,
            None,
        ),
        (
            "a: Int\nb: Int",
            "a > b and b > 0",
            False,
            None,
        ),
        (
            "name: Str\nage: Int",
            "name = 'John' and age >= 18",
            False,
            None,
        ),
        (
            "amount: Int",
            "amount > unknown_var",
            True,
            "Unknown variable: unknown_var",
        ),
        (
            "amount: Int",
            "amount > 0 and",
            True,
            "Unexpected end of expression",
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
        assert hasattr(rule_ast, "variables")
        assert hasattr(rule_ast, "functions")


@pytest.mark.parametrize(
    "schema_content,rule,expected_operator,left_type,left_value,right_type,right_value,expected_variables",
    [
        ("amount: Int", "amount > 100", Operator.GT, Variable, "amount", Literal, 100, ["amount"]),
        ("amount: Int", "100 > 50", Operator.GT, Literal, 100, Literal, 50, []),
        ("name: Str", "name = 'John'", Operator.EQ, Variable, "name", Literal, "John", ["name"]),
        ("name: Str", 'name = "Jane"', Operator.EQ, Variable, "name", Literal, "Jane", ["name"]),
    ],
)
def test_simple_comparisons(
    schema_content, rule, expected_operator, left_type, left_value, right_type, right_value, expected_variables
):
    """Test parsing simple comparisons."""
    schema_ast = parse_schema(schema_content)
    rule_ast = parse_rule(rule, schema_ast)

    assert isinstance(rule_ast.root, BinaryOp)
    assert rule_ast.root.operator == expected_operator

    assert isinstance(rule_ast.root.left, left_type)
    if left_type == Variable:
        assert isinstance(rule_ast.root.left, Variable)
        assert rule_ast.root.left.name == left_value
    else:
        assert isinstance(rule_ast.root.left, Literal)
        assert rule_ast.root.left.value == left_value

    assert isinstance(rule_ast.root.right, right_type)
    if right_type == Variable:
        assert isinstance(rule_ast.root.right, Variable)
        assert rule_ast.root.right.name == right_value
    else:
        assert isinstance(rule_ast.root.right, Literal)
        assert rule_ast.root.right.value == right_value

    for var in expected_variables:
        assert var in rule_ast.variables


@pytest.mark.parametrize(
    "schema_content,rule,expected_variables",
    [
        ("amount: Int\nstate: Str", "amount > 0 and state = 'CA'", ["amount", "state"]),
        ("a: Int\nb: Int\nc: Int", "(a > 0 and b > 0) or c > 0", ["a", "b", "c"]),
    ],
)
def test_complex_expressions(schema_content, rule, expected_variables):
    """Test parsing complex logical expressions."""
    schema_ast = parse_schema(schema_content)
    rule_ast = parse_rule(rule, schema_ast)

    assert isinstance(rule_ast.root, BinaryOp)

    for var in expected_variables:
        assert var in rule_ast.variables


def test_function_calls():
    """Test parsing function calls."""
    schema_ast = parse_schema("amount: Int\nmax_amount: Int\nmin_func: (a: Int, b: Int) -> int")
    rule_ast = parse_rule("min_func(amount, max_amount) > 0", schema_ast)

    assert isinstance(rule_ast.root, BinaryOp)
    assert "min_func" in rule_ast.functions


def test_struct_field_access():
    """Test parsing struct field access."""
    schema_ast = parse_schema("""
    struct person {
        name: Str,
        age: Int
    }
    """)
    rule_ast = parse_rule("person.age > 18", schema_ast)

    assert isinstance(rule_ast.root, BinaryOp)
    assert isinstance(rule_ast.root.left, Variable)
    assert rule_ast.root.left.name == "person.age"
