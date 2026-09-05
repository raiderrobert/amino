import pytest

import amino
from amino.backends import Query, UnsupportedExpressionError
from amino.backends.clickhouse import ClickHouseBackend

SCHEMA = """
struct Customer { id: Str, tier: Int }
score: Int
ratio: Float
name: Str
active: Bool
contact: email
customer: Customer
"""


@pytest.fixture
def engine():
    return amino.load_schema(SCHEMA)


def compile_ch(engine, text, **kw) -> Query:
    return ClickHouseBackend(**kw).compile(engine.parse(text))


@pytest.mark.parametrize(
    "text, sql, params",
    [
        ("score = 5", "(`score` = {p0:Int64})", {"p0": 5}),
        ("score != 5", "(`score` <> {p0:Int64})", {"p0": 5}),
        ("score > 5", "(`score` > {p0:Int64})", {"p0": 5}),
        ("score < 5", "(`score` < {p0:Int64})", {"p0": 5}),
        ("score >= 5", "(`score` >= {p0:Int64})", {"p0": 5}),
        ("score <= 5", "(`score` <= {p0:Int64})", {"p0": 5}),
        ("ratio > 0.5", "(`ratio` > {p0:Float64})", {"p0": 0.5}),
        ("name = 'bob'", "(`name` = {p0:String})", {"p0": "bob"}),
        ("active = true", "(`active` = {p0:Bool})", {"p0": True}),
        ("contact = 'a@b.co'", "(`contact` = {p0:String})", {"p0": "a@b.co"}),
        ("name in ['a', 'b']", "(`name` IN {p0:Array(String)})", {"p0": ["a", "b"]}),
        ("name not in ['a', 'b']", "(`name` NOT IN {p0:Array(String)})", {"p0": ["a", "b"]}),
        ("score in [1, 2, 3]", "(`score` IN {p0:Array(Int64)})", {"p0": [1, 2, 3]}),
        ("ratio in [0.5, 1.5]", "(`ratio` IN {p0:Array(Float64)})", {"p0": [0.5, 1.5]}),
        ("name in []", "FALSE", {}),
        ("name not in []", "TRUE", {}),
        ("name contains 'ob'", "(position(`name`, {p0:String}) > 0)", {"p0": "ob"}),
        ("not active = true", "(NOT (`active` = {p0:Bool}))", {"p0": True}),
        (
            "score > 1 and name = 'x'",
            "((`score` > {p0:Int64}) AND (`name` = {p1:String}))",
            {"p0": 1, "p1": "x"},
        ),
        (
            "score > 1 or name = 'x' and active = false",
            "((`score` > {p0:Int64}) OR ((`name` = {p1:String}) AND (`active` = {p2:Bool})))",
            {"p0": 1, "p1": "x", "p2": False},
        ),
    ],
)
def test_standard_operators(engine, text, sql, params):
    q = compile_ch(engine, text)
    assert q.sql == sql
    assert q.params == params


def test_column_mapping_renders_fragment_verbatim(engine):
    q = compile_ch(engine, "customer.tier > 2", columns={"customer.tier": "customer.tier"})
    assert q.sql == "(customer.tier > {p0:Int64})"
    assert q.params == {"p0": 2}


def test_dotted_path_without_mapping_is_unsupported(engine):
    with pytest.raises(UnsupportedExpressionError, match=r"customer\.tier"):
        compile_ch(engine, "customer.tier > 2")


def test_custom_operator_is_unsupported():
    engine = amino.load_schema("a: Int\nb: Int")
    engine.register_operator(
        keyword="near",
        fn=lambda x, y: abs(x - y) < 5,
        binding_power=40,
        input_types=("Int", "Int"),
        return_type="Bool",
    )
    with pytest.raises(UnsupportedExpressionError, match="near"):
        compile_ch(engine, "a near b")


def test_function_call_emits_name_and_args():
    engine = amino.load_schema("name: Str\nlower: (s: Str) -> Str")
    q = compile_ch(engine, "lower(name) = 'x'")
    assert q.sql == "(lower(`name`) = {p0:String})"
    assert q.params == {"p0": "x"}


def test_identifier_quoting_escapes_backticks():
    assert ClickHouseBackend().quote_ident("we`ird") == "`we\\`ird`"
