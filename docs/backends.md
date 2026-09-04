# Compile Targets (Backends)

An amino expression is parsed and type-checked once, then compiled by a
backend into whatever a particular system executes. The in-process Python
evaluator behind `engine.compile()` / `engine.eval()` is one target. This
document covers the SQL targets.

## Parsing an expression

```python
import amino

engine = amino.load_schema("""
score: Int
name: Str
active: Bool
""")

expr = engine.parse("score > 40 and name contains 'ob'")
```

`engine.parse()` freezes the engine exactly like `compile()` does, because
operator resolution happens at parse time. The returned `Expression` is
backend-agnostic: hand the same one to any number of backends.

## Postgres

```python
from amino.backends.postgres import PostgresBackend

q = PostgresBackend().compile(expr)
q.sql     # '(("score" > %s) AND (position(%s IN "name") > 0))'
q.params  # [40, 'ob']

with conn.cursor() as cur:
    cur.execute(f"SELECT id FROM users WHERE {q.sql}", q.params)
```

Parameters are psycopg positional placeholders. List membership renders as
`col = ANY(%s)` so the whole Python list binds as one array parameter.

## ClickHouse

```python
from amino.backends.clickhouse import ClickHouseBackend

q = ClickHouseBackend().compile(expr)
q.sql     # '((`score` > {p0:Int64}) AND (position(`name`, {p1:String}) > 0))'
q.params  # {'p0': 40, 'p1': 'ob'}

client.query(f"SELECT id FROM users WHERE {q.sql}", parameters=q.params)
```

Placeholders are ClickHouse server-side typed parameters. The type comes
from the schema, so a `Str` field binds as `String`, an `Int` as `Int64`, a
`Float` as `Float64`, a `Bool` as `Bool`, and a list as `Array(T)`. Custom
types (`email`, `ipv4`) bind as their base type.

## Operator rendering

| DSL | Postgres | ClickHouse |
|---|---|---|
| `=` `!=` `<` `>` `<=` `>=` | same, `!=` becomes `<>` | same |
| `and` `or` `not` | `AND` `OR` `NOT`, every node parenthesised | same |
| `x in [..]` | `x = ANY(%s)` | `x IN {p:Array(T)}` |
| `x not in [..]` | `NOT (x = ANY(%s))` | `x NOT IN {p:Array(T)}` |
| `x in []` / `x not in []` | `FALSE` / `TRUE` | `FALSE` / `TRUE` |
| `x contains 'y'` | `position(%s IN x) > 0` | `position(x, {p:String}) > 0` |
| `fn(a, b)` | `fn(a, b)` | `fn(a, b)` |

Function calls are emitted by name with no mapping. The function must exist
in the target database.

## Column mapping

Field names become quoted identifiers by default. Nested struct fields have
no default rendering and must be mapped. Mapping also covers tables whose
column names differ from the schema:

```python
backend = PostgresBackend(columns={
    "customer.tier": "customer_tier",
    "score": "s.score",
})
```

Mapped values are spliced into the SQL verbatim. They are trusted fragments
written by the integrator, never user input. Everything the user writes in
the expression is bound as a parameter.

## What raises

Backends never degrade silently. `UnsupportedExpressionError` is raised for:

- a nested field with no column mapping
- a custom operator registered with `register_operator()`
- `in` / `not in` whose right side is not a list literal
- a list literal anywhere other than the right of `in` / `not in`

## Semantics that differ from the Python evaluator

**NULL.** SQL uses three-valued logic. `score > 5` on a NULL `score` is
neither true nor false, and `NOT` of that is still unknown. The Python
evaluator treats a missing field as "this rule is false". Expressions over
optional (`Str?`) fields can therefore select different rows. Prefer `NOT
NULL` columns for fields the DSL filters on.

**String comparison.** Postgres `=` and `position()` follow the column's
collation. ClickHouse compares bytes. The Python evaluator compares Unicode
code points. ASCII data behaves identically everywhere.

## Testing

`tests/integration/test_sql_parity.py` runs every expression in its list
through Postgres, ClickHouse and the Python evaluator against the same rows
and asserts all three select the same ids. It needs local databases:

```bash
make db-up              # starts postgres:16 on :55432 and clickhouse:24.8 on :18123
make test-integration   # runs the parity suite
make db-down
```

`make test` runs the same tests but skips them when a database is
unreachable. Override the connection strings with `AMINO_PG_DSN` and
`AMINO_CH_URL`.

Driver packages are optional extras: `pip install amino[postgres]` or
`amino[clickhouse]`. The backends themselves import neither; only your code
and the integration tests do.
