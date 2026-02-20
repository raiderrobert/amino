import pytest
from amino.operators.standard import build_operator_registry
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.rules.parser import parse_rule
from amino.rules.compiler import TypedCompiler
from amino.errors import TypeMismatchError

SCHEMA = "score: Int\nname: Str\nactive: Bool\ntags: List[Str]"

def _compile(rule: str, rules_mode: str = "strict"):
    reg = SchemaRegistry(parse_schema(SCHEMA))
    ops = build_operator_registry("standard")
    ast = parse_rule(rule, reg, ops)
    compiler = TypedCompiler(rules_mode=rules_mode)
    return compiler.compile("r1", ast)

def test_simple_equality_evaluates():
    compiled = _compile("score = 500")
    assert compiled.evaluate({"score": 500}, {}) is True
    assert compiled.evaluate({"score": 400}, {}) is False

def test_and_short_circuits():
    compiled = _compile("active = true and score > 100")
    assert compiled.evaluate({"active": False, "score": 0}, {}) is False

def test_or_evaluates():
    compiled = _compile("score < 0 or score > 1000")
    assert compiled.evaluate({"score": 1500}, {}) is True

def test_not_evaluates():
    compiled = _compile("not active")
    assert compiled.evaluate({"active": False}, {}) is True

def test_in_list():
    compiled = _compile("name in ['alice', 'bob']")
    assert compiled.evaluate({"name": "alice"}, {}) is True
    assert compiled.evaluate({"name": "carol"}, {}) is False

def test_contains_operator():
    compiled = _compile("name contains 'ali'")
    assert compiled.evaluate({"name": "alice"}, {}) is True

def test_function_call():
    compiled = _compile("score = 42")
    fns = {}
    assert compiled.evaluate({"score": 42}, fns) is True

def test_dot_notation():
    schema = "struct Addr { city: Str }\naddr: Addr"
    reg = SchemaRegistry(parse_schema(schema))
    ops = build_operator_registry("standard")
    ast = parse_rule("addr.city = 'SF'", reg, ops)
    compiled = TypedCompiler().compile("r1", ast)
    assert compiled.evaluate({"addr": {"city": "SF"}}, {}) is True

def test_constant_folding():
    compiled = _compile("true = true")
    assert compiled.evaluate({}, {}) is True

def test_missing_field_returns_false():
    compiled = _compile("score > 100")
    # missing field → evaluates to False, no exception (loose runtime)
    assert compiled.evaluate({}, {}) is False
