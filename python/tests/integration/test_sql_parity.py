"""Every expression must select the same rows on Postgres, ClickHouse and the
in-process Python evaluator. This is the contract that makes the backends
interchangeable."""

import pytest

import amino
from amino.backends.clickhouse import ClickHouseBackend
from amino.backends.postgres import PostgresBackend

from .conftest import ROWS, TABLE

pytestmark = pytest.mark.integration

SCHEMA = """
struct Meta { tier: Int }
score: Int
ratio: Float
name: Str
active: Bool
contact: email
meta: Meta
"""

COLUMN_MAP = {"meta.tier": "meta_tier"}

EXPRESSIONS = [
    "score = 100",
    "score != 100",
    "score > 50",
    "score < 50",
    "score >= 100",
    "score <= 0",
    "ratio > 0.5",
    "ratio <= 0.42",
    "name = 'bob'",
    "name contains 'Neil'",
    "active = true",
    "active = false",
    "contact = 'alice@example.com'",
    "name in ['alice', 'bob', 'nobody']",
    "name not in ['alice', 'bob']",
    "score in [0, 7, 42]",
    "ratio in [0.25, 1.0]",
    "name in []",
    "name not in []",
    "name contains 'ob'",
    "contact contains '@example.org'",
    "not active = true",
    "score > 40 and active = true",
    "score > 900 or name = 'judy'",
    "score > 1 or name = 'alice' and active = false",
    "(score > 1 or name = 'alice') and active = false",
    "meta.tier = 2",
    "meta.tier in [1, 3] and score >= 100",
    "not (score > 50 or ratio < 0.1)",
]


def _nested(row: dict) -> dict:
    """Python evaluator sees ``meta.tier`` as a nested dict, not a flat column."""
    out = {k: v for k, v in row.items() if k != "meta_tier"}
    out["meta"] = {"tier": row["meta_tier"]}
    return out


PY_ROWS = [_nested(r) for r in ROWS]


@pytest.fixture(scope="module")
def engine():
    return amino.load_schema(SCHEMA)


def python_ids(engine, text: str) -> set[int]:
    compiled = engine.compile([{"id": "r", "rule": text}])
    return {res.id for res in compiled.eval(PY_ROWS) if "r" in res.matched}


def postgres_ids(engine, pg_conn, text: str) -> set[int]:
    q = PostgresBackend(columns=COLUMN_MAP).compile(engine.parse(text))
    with pg_conn.cursor() as cur:
        cur.execute(f"SELECT id FROM {TABLE} WHERE {q.sql}", q.params)
        return {row[0] for row in cur.fetchall()}


def clickhouse_ids(engine, ch_client, text: str) -> set[int]:
    q = ClickHouseBackend(columns=COLUMN_MAP).compile(engine.parse(text))
    result = ch_client.query(f"SELECT id FROM {TABLE} WHERE {q.sql}", parameters=q.params)
    return {row[0] for row in result.result_rows}


@pytest.mark.parametrize("text", EXPRESSIONS)
def test_three_backends_agree(engine, pg_conn, ch_client, text):
    expected = python_ids(engine, text)
    assert postgres_ids(engine, pg_conn, text) == expected, "postgres disagrees with python"
    assert clickhouse_ids(engine, ch_client, text) == expected, "clickhouse disagrees with python"


def test_fixture_covers_every_row_at_least_once(engine, pg_conn, ch_client):
    """Guard against a data set that trivially matches nothing."""
    seen: set[int] = set()
    for text in EXPRESSIONS:
        seen |= python_ids(engine, text)
    assert seen == {r["id"] for r in ROWS}
