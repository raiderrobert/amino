"""Fixtures for running expressions against real Postgres and ClickHouse.

Both fixtures skip when their database is unreachable, so ``pytest tests``
stays green on a machine without Docker. Start the databases with
``scripts/dev-db.sh up`` (or ``make db-up``).
"""

import os
from collections.abc import Iterator
from typing import Any

import pytest

PG_DSN = os.environ.get("AMINO_PG_DSN", "postgresql://amino:amino@localhost:55432/amino")
CH_URL = os.environ.get("AMINO_CH_URL", "http://amino:amino@localhost:18123/amino")

TABLE = "amino_parity"

COLUMNS = ["id", "score", "ratio", "name", "active", "contact", "meta_tier"]

# One flat row per record. ``meta_tier`` backs the nested ``meta.tier`` field
# via a column mapping on the SQL side and a nested dict on the Python side.
_ROW_TUPLES: list[tuple[Any, ...]] = [
    (1, 0, 0.0, "alice", True, "alice@example.com", 1),
    (2, 10, 0.25, "bob", False, "bob@example.com", 1),
    (3, 50, 0.5, "carol", True, "carol@example.org", 2),
    (4, 100, 0.75, "dave", False, "dave@example.org", 2),
    (5, 150, 1.0, "erin", True, "erin@example.net", 3),
    (6, -5, -0.5, "frank", False, "frank@example.net", 3),
    (7, 100, 2.5, "grace", True, "grace@example.com", 1),
    (8, 42, 0.42, "heidi", True, "heidi@example.com", 2),
    (9, 1000, 10.0, "ivan", False, "ivan@example.org", 3),
    (10, 7, 0.07, "judy", True, "judy@example.net", 1),
    (11, 99, 0.99, "bobby", False, "bobby@example.com", 2),
    (12, 100, 1.5, "O'Neil", True, "oneil@example.com", 3),
]
ROWS: list[dict[str, Any]] = [dict(zip(COLUMNS, t, strict=True)) for t in _ROW_TUPLES]


def _row_values(row: dict[str, Any]) -> list[Any]:
    return [row[c] for c in COLUMNS]


@pytest.fixture(scope="session")
def pg_conn() -> Iterator[Any]:
    psycopg = pytest.importorskip("psycopg")
    try:
        conn = psycopg.connect(PG_DSN, connect_timeout=3)
    except Exception as exc:
        pytest.skip(f"Postgres not reachable at {PG_DSN}: {exc}")
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
        cur.execute(
            f"CREATE TABLE {TABLE} ("
            "id bigint PRIMARY KEY, score bigint NOT NULL, ratio double precision NOT NULL, "
            "name text NOT NULL, active boolean NOT NULL, contact text NOT NULL, meta_tier bigint NOT NULL)"
        )
        cur.executemany(
            f"INSERT INTO {TABLE} ({', '.join(COLUMNS)}) VALUES ({', '.join('%s' for _ in COLUMNS)})",
            [_row_values(r) for r in ROWS],
        )
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def ch_client() -> Iterator[Any]:
    clickhouse_connect = pytest.importorskip("clickhouse_connect")
    try:
        client = clickhouse_connect.get_client(dsn=CH_URL, connect_timeout=3)
        client.command("SELECT 1")
    except Exception as exc:
        pytest.skip(f"ClickHouse not reachable at {CH_URL}: {exc}")
    client.command(f"DROP TABLE IF EXISTS {TABLE}")
    client.command(
        f"CREATE TABLE {TABLE} ("
        "id Int64, score Int64, ratio Float64, name String, active Bool, contact String, meta_tier Int64"
        ") ENGINE = MergeTree ORDER BY id"
    )
    client.insert(TABLE, [_row_values(r) for r in ROWS], column_names=COLUMNS)
    yield client
    client.close()
