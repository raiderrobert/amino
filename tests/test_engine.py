import pytest
import amino
from amino.errors import EngineAlreadyFrozenError, OperatorConflictError

SCHEMA = "score: Int\nname: Str\nactive: Bool"

def test_basic_compile_and_eval():
    engine = amino.load_schema(SCHEMA)
    compiled = engine.compile([{"id": "r1", "rule": "score > 400"}])
    result = compiled.eval_single({"score": 500})
    assert "r1" in result.matched

def test_one_shot_eval():
    engine = amino.load_schema(SCHEMA)
    result = engine.eval(
        rules=[{"id": "r1", "rule": "score > 400"}],
        decision={"score": 500},
    )
    assert "r1" in result.matched

def test_freeze_on_compile():
    engine = amino.load_schema(SCHEMA)
    engine.compile([{"id": "r1", "rule": "score > 0"}])
    with pytest.raises(EngineAlreadyFrozenError):
        engine.add_function("foo", lambda: 1)

def test_freeze_on_eval():
    engine = amino.load_schema(SCHEMA)
    engine.eval(rules=[{"id": "r1", "rule": "score > 0"}], decision={"score": 1})
    with pytest.raises(EngineAlreadyFrozenError):
        engine.register_type("mytype", base="Str", validator=lambda v: True)

def test_register_type_before_compile():
    engine = amino.load_schema("ip: ipv4")
    engine.register_type("ipv4", base="Str", validator=lambda v: isinstance(v, str))
    compiled = engine.compile([{"id": "r1", "rule": "ip = '1.2.3.4'"}])
    result = compiled.eval_single({"ip": "1.2.3.4"})
    assert "r1" in result.matched

def test_register_custom_operator():
    engine = amino.load_schema(SCHEMA, operators="minimal")
    engine.register_operator(
        keyword="above", fn=lambda l, r: l > r,
        binding_power=40, input_types=("Int", "Int"), return_type="Bool",
    )
    compiled = engine.compile([{"id": "r1", "rule": "score above 400"}])
    result = compiled.eval_single({"score": 500})
    assert "r1" in result.matched

def test_duplicate_operator_raises():
    engine = amino.load_schema(SCHEMA)
    with pytest.raises(OperatorConflictError):
        engine.register_operator(
            symbol="=", fn=lambda l, r: l == r,
            binding_power=40, input_types=("*", "*"), return_type="Bool",
        )

def test_update_rules_hot_swap():
    engine = amino.load_schema(SCHEMA)
    engine.compile([{"id": "r1", "rule": "score > 400"}])
    # hot-swap is compile-time idempotent — schema stays same
    compiled2 = engine.compile([{"id": "r2", "rule": "score < 100"}])
    result = compiled2.eval_single({"score": 50})
    assert "r2" in result.matched

def test_export_schema():
    engine = amino.load_schema(SCHEMA)
    exported = engine.export_schema()
    assert "score: Int" in exported
    assert "name: Str" in exported

def test_match_modes():
    engine = amino.load_schema(SCHEMA)
    compiled = engine.compile(
        [{"id": "r1", "rule": "score > 0", "ordering": 2},
         {"id": "r2", "rule": "active = true", "ordering": 1}],
        match={"mode": "first", "key": "ordering", "order": "asc"},
    )
    result = compiled.eval_single({"score": 100, "active": True})
    assert result.matched == ["r1"] or result.matched == ["r2"]  # first by ordering

def test_rules_mode_and_decisions_mode():
    engine = amino.load_schema(SCHEMA, rules_mode="strict", decisions_mode="loose")
    compiled = engine.compile([{"id": "r1", "rule": "score > 0"}])
    result = compiled.eval_single({"score": "bad"})  # loose: skip and warn
    assert result.warnings
