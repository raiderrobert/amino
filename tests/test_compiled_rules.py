from amino.operators.standard import build_operator_registry
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.rules.parser import parse_rule
from amino.rules.compiler import TypedCompiler
from amino.runtime.compiled_rules import CompiledRules
from amino.runtime.validator import DecisionValidator

SCHEMA = "score: Int\nname: Str"


def _make_compiled(rules: list[dict], match: dict | None = None):
    reg = SchemaRegistry(parse_schema(SCHEMA))
    ops = build_operator_registry("standard")
    compiler = TypedCompiler()
    compiled_list = []
    for r in rules:
        ast = parse_rule(r["rule"], reg, ops)
        compiled_list.append((r["id"], compiler.compile(r["id"], ast), r))
    validator = DecisionValidator(reg, decisions_mode="loose")
    return CompiledRules(compiled_list, validator, match_config=match)


def test_eval_single_all_mode():
    cr = _make_compiled([
        {"id": "r1", "rule": "score > 400"},
        {"id": "r2", "rule": "name = 'alice'"},
    ])
    result = cr.eval_single({"score": 500, "name": "bob"})
    assert "r1" in result.matched
    assert "r2" not in result.matched


def test_eval_single_first_mode():
    cr = _make_compiled([
        {"id": "r1", "rule": "score > 400", "ordering": 2},
        {"id": "r2", "rule": "score > 100", "ordering": 1},
    ], match={"mode": "first", "key": "ordering", "order": "asc"})
    result = cr.eval_single({"score": 500, "name": "x"})
    assert result.matched == ["r2"]


def test_eval_batch():
    cr = _make_compiled([{"id": "r1", "rule": "score > 400"}])
    results = cr.eval([{"score": 500}, {"score": 200}])
    assert "r1" in results[0].matched
    assert "r1" not in results[1].matched


def test_warnings_from_loose_validation():
    cr = _make_compiled([{"id": "r1", "rule": "score > 0"}])
    result = cr.eval_single({"score": "not-an-int"})  # wrong type, loose mode
    assert result.warnings  # validator added a warning
