# tests/test_rule_parser.py
import pytest
from amino.operators.standard import build_operator_registry
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.rules.parser import parse_rule
from amino.rules.ast import BinaryOp, Literal, UnaryOp, Variable
from amino.errors import RuleParseError

def _parse(rule: str, schema: str = "score: Int\nname: Str\nactive: Bool\ntags: List[Str]"):
    reg = SchemaRegistry(parse_schema(schema))
    ops = build_operator_registry("standard")
    return parse_rule(rule, reg, ops)

def test_integer_literal():
    ast = _parse("500")
    assert isinstance(ast.root, Literal) and ast.root.value == 500

def test_float_before_integer():
    ast = _parse("600.0")
    assert isinstance(ast.root, Literal) and ast.root.value == 600.0

def test_string_literal():
    ast = _parse("'hello'")
    assert isinstance(ast.root, Literal) and ast.root.value == "hello"

def test_boolean_literal():
    ast = _parse("true")
    assert isinstance(ast.root, Literal) and ast.root.value is True

def test_variable_reference():
    ast = _parse("score")
    assert isinstance(ast.root, Variable) and ast.root.name == "score"

def test_simple_comparison():
    ast = _parse("score = 500")
    assert isinstance(ast.root, BinaryOp)
    assert ast.root.op_token == "="

def test_comparison_precedence_over_and():
    ast = _parse("score > 400 and score < 800")
    assert isinstance(ast.root, BinaryOp)
    assert ast.root.op_token == "and"

def test_not_prefix():
    ast = _parse("not active")
    assert isinstance(ast.root, UnaryOp) and ast.root.op_token == "not"

def test_parentheses_grouping():
    ast = _parse("(score > 400 or score < 100) and active = true")
    root = ast.root
    assert root.op_token == "and"

def test_in_list_membership():
    ast = _parse("name in ['foo', 'bar']")
    assert ast.root.op_token == "in"

def test_not_in():
    ast = _parse("name not in ['a', 'b']")
    assert ast.root.op_token == "not in"

def test_contains_operator():
    ast = _parse("name contains 'ell'")
    assert ast.root.op_token == "contains"

def test_function_call():
    schema = "score: Int\ncheck: (x: Int) -> Bool"
    ast = _parse("check(score)", schema=schema)
    from amino.rules.ast import FunctionCall
    assert isinstance(ast.root, FunctionCall) and ast.root.name == "check"

def test_dot_notation():
    schema = "struct Addr { city: Str }\naddr: Addr"
    ast = _parse("addr.city = 'SF'", schema=schema)
    assert isinstance(ast.root, BinaryOp)
    assert isinstance(ast.root.left, Variable)
    assert ast.root.left.name == "addr.city"

def test_unknown_variable_raises():
    with pytest.raises(RuleParseError, match="Unknown"):
        _parse("unknown_field = 1")

def test_list_literal_in_rule():
    ast = _parse("tags in [['a', 'b']]")  # tags is List[Str], comparing with list literal
    assert ast.root.op_token == "in"

def test_or_lower_precedence_than_and():
    # a or b and c  should parse as  a or (b and c)
    ast = _parse("active = true or score > 0 and score < 100")
    assert ast.root.op_token == "or"
    assert ast.root.right.op_token == "and"
