import pytest

import amino
from amino.errors import EngineAlreadyFrozenError, RuleParseError
from amino.expression import Expression
from amino.rules.ast import BinaryOp, Variable

SCHEMA = "score: Int\nname: Str\ncontact: email"


def test_parse_returns_typed_expression():
    engine = amino.load_schema(SCHEMA)
    expr = engine.parse("score > 400 and name = 'x'")
    assert isinstance(expr, Expression)
    assert isinstance(expr.ast.root, BinaryOp)
    assert expr.ast.return_type == "Bool"


def test_parse_freezes_engine():
    engine = amino.load_schema(SCHEMA)
    engine.parse("score > 0")
    with pytest.raises(EngineAlreadyFrozenError):
        engine.add_function("foo", lambda: 1)


def test_parse_rejects_unknown_field():
    engine = amino.load_schema(SCHEMA)
    with pytest.raises(RuleParseError):
        engine.parse("missing > 0")


def test_base_type_resolves_custom_and_builtin():
    engine = amino.load_schema(SCHEMA)
    expr = engine.parse("contact = 'a@b.co'")
    assert isinstance(expr.ast.root, BinaryOp)
    left = expr.ast.root.left
    assert isinstance(left, Variable)
    assert left.type_name == "email"
    assert expr.base_type("email") == "Str"
    assert expr.base_type("Int") == "Int"
    assert expr.base_type("List") == "List"
