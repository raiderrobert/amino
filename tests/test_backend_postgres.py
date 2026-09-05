import pytest

import amino
from amino.backends import Query, UnsupportedExpressionError
from amino.backends.postgres import PostgresBackend

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


def compile_pg(engine, text, **kw) -> Query:
    return PostgresBackend(**kw).compile(engine.parse(text))


@pytest.mark.parametrize(
    "text, sql, params",
    [
        ("score = 5", '("score" = %s)', [5]),
        ("score != 5", '("score" <> %s)', [5]),
        ("score > 5", '("score" > %s)', [5]),
        ("score < 5", '("score" < %s)', [5]),
        ("score >= 5", '("score" >= %s)', [5]),
        ("score <= 5", '("score" <= %s)', [5]),
        ("ratio > 0.5", '("ratio" > %s)', [0.5]),
        ("name = 'bob'", '("name" = %s)', ["bob"]),
        ("active = true", '("active" = %s)', [True]),
        ("contact = 'a@b.co'", '("contact" = %s)', ["a@b.co"]),
        ("name in ['a', 'b']", '("name" = ANY(%s))', [["a", "b"]]),
        ("name not in ['a', 'b']", '(NOT ("name" = ANY(%s)))', [["a", "b"]]),
        ("score in [1, 2, 3]", '("score" = ANY(%s))', [[1, 2, 3]]),
        ("name in []", "FALSE", []),
        ("name not in []", "TRUE", []),
        ("name contains 'ob'", '(position(%s IN "name") > 0)', ["ob"]),
        ("not active = true", '(NOT ("active" = %s))', [True]),
        (
            "score > 1 and name = 'x'",
            '(("score" > %s) AND ("name" = %s))',
            [1, "x"],
        ),
        (
            "score > 1 or name = 'x'",
            '(("score" > %s) OR ("name" = %s))',
            [1, "x"],
        ),
        (
            "score > 1 or name = 'x' and active = false",
            '(("score" > %s) OR (("name" = %s) AND ("active" = %s)))',
            [1, "x", False],
        ),
        (
            "(score > 1 or name = 'x') and active = false",
            '((("score" > %s) OR ("name" = %s)) AND ("active" = %s))',
            [1, "x", False],
        ),
    ],
)
def test_standard_operators(engine, text, sql, params):
    q = compile_pg(engine, text)
    assert q.sql == sql
    assert q.params == params


def test_column_mapping_renders_fragment_verbatim(engine):
    q = compile_pg(engine, "customer.tier > 2", columns={"customer.tier": "customer_tier"})
    assert q.sql == "(customer_tier > %s)"
    assert q.params == [2]


def test_column_mapping_overrides_top_level_field(engine):
    q = compile_pg(engine, "score > 2", columns={"score": "s.score"})
    assert q.sql == "(s.score > %s)"


def test_dotted_path_without_mapping_is_unsupported(engine):
    with pytest.raises(UnsupportedExpressionError, match=r"customer\.tier"):
        compile_pg(engine, "customer.tier > 2")


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
        compile_pg(engine, "a near b")


def test_function_call_emits_name_and_args():
    engine = amino.load_schema("name: Str\nlower: (s: Str) -> Str")
    q = compile_pg(engine, "lower(name) = 'x'")
    assert q.sql == '(lower("name") = %s)'
    assert q.params == ["x"]


def test_identifier_quoting_escapes_double_quotes():
    engine = amino.load_schema("a: Int")
    q = PostgresBackend(columns={}).compile(engine.parse("a = 1"))
    assert q.sql == '("a" = %s)'
    assert PostgresBackend().quote_ident('we"ird') == '"we""ird"'


def test_query_is_immutable(engine):
    q = compile_pg(engine, "score = 1")
    with pytest.raises((AttributeError, TypeError)):
        q.sql = "x"  # type: ignore[misc]
