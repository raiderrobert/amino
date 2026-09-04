# SQL Backends: Postgres and ClickHouse

**Date**: 2026-09-03
**Status**: Approved (direction agreed in session; scope set via `/goal`)

## Context

Amino is being reframed from "a rules engine" to "a toolkit for small typed
DSLs, with pluggable compile targets". The rules engine (in-process evaluator
plus matcher) becomes one target. This spec adds the first two external
targets: Postgres and ClickHouse. Both compile a typed amino expression into a
parameterised SQL predicate suitable for a `WHERE` clause.

The driving use case is a single query language on the front end that is
dispatched to different storage back ends.

## Scope

In scope:

- `Engine.parse(text) -> Expression`: parse and type-check one expression
  against the schema and return a backend-agnostic typed AST wrapper.
- `amino.backends.postgres.PostgresBackend` and
  `amino.backends.clickhouse.ClickHouseBackend`, each with
  `compile(expr) -> Query`.
- `Query` is `(sql: str, params)`. Parameters are always bound, never
  inlined. Postgres uses psycopg positional `%s` with a list; ClickHouse uses
  server-side typed placeholders `{p0:Int64}` with a dict.
- Optional per-backend column mapping so a DSL field path can be rendered as
  any column expression (`columns={"customer.id": "customer_id"}`).
- Unit tests asserting exact SQL and params, with no database.
- Integration tests that run each expression through Postgres, ClickHouse and
  the existing Python evaluator against the same rows and assert all three
  agree. They run against local Docker containers and skip when the database
  is unreachable.

Out of scope for this change (follow-ups):

- Moving the Python evaluator under `amino.backends`. It stays where it is.
- Projections, sorting, pagination, aggregation. Predicates only.
- Per-backend function name mapping. Function calls emit `name(args)` as-is.
- NULL semantics parity. SQL uses three-valued logic; the Python evaluator
  treats a missing field as "rule is false". The integration tests avoid NULL
  columns. This is documented, not solved.

## Design

### Expression

```python
@dataclass(frozen=True)
class Expression:
    ast: RuleAST
    schema: SchemaRegistry
    types: TypeRegistry

    def base_type(self, type_name: str) -> str
        # "email" -> "Str", "Int" -> "Int", "List" -> "List"
```

`Engine.parse()` freezes the engine exactly like `compile()` does, because
parsing resolves operators from the registry.

### Backend contract

`SQLBackend` is an abstract base holding the shared tree walk. Dialects
override only what differs:

| Hook | Postgres | ClickHouse |
|---|---|---|
| `placeholder(index, value, base_type)` | `%s`, appends to list | `{pN:Type}`, adds to dict |
| `quote_ident(name)` | `"name"` | `` `name` `` |
| `render_in(col, placeholder)` | `col = ANY(%s)` | `col IN {pN:Array(T)}` |
| `render_contains(haystack, needle)` | `position(needle IN haystack) > 0` | `position(haystack, needle) > 0` |
| `param_type(base_type)` | unused | `Int64`, `Float64`, `String`, `Bool` |

Operator rendering for `= != < > <= >= and or not` is shared. `!=` renders
as `<>`. `and` / `or` render with explicit parentheses around every binary
node so precedence never depends on the target dialect.

Unsupported nodes (a dotted field with no column mapping, an operator the
backend has no rendering for, a custom operator registered by the user) raise
`UnsupportedExpressionError(AminoError)`. Backends never silently degrade.

### Column mapping

`SQLBackend(columns: dict[str, str] | None = None)`. On a `Variable` node the
backend first checks the mapping and emits the value verbatim if present.
Otherwise a top-level field emits its quoted name and a dotted path raises
`UnsupportedExpressionError`. Mapped values are trusted SQL fragments written
by the engineer, not user input.

### Type handling

Literal types come from the parser: `Int`, `Float`, `Str`, `Bool`, `List`.
Custom types on variables (`ipv4`, `email`) resolve to their base via
`Expression.base_type`. For `in`, the list's element type is inferred from
the first element's Python type. An empty list renders as `FALSE` for `in`
and `TRUE` for `not in`, matching Python semantics.

### Module layout

```
amino/backends/__init__.py     # exports Query, UnsupportedExpressionError
amino/backends/base.py         # Query, SQLBackend
amino/backends/postgres.py     # PostgresBackend
amino/backends/clickhouse.py   # ClickHouseBackend
amino/expression.py            # Expression
tests/test_backend_postgres.py
tests/test_backend_clickhouse.py
tests/integration/conftest.py  # docker connections, skip logic
tests/integration/test_sql_parity.py
docker-compose.yml             # postgres:16 on 55432, clickhouse 24.8 on 58123
```

Driver dependencies are optional extras: `amino[postgres]` pulls
`psycopg[binary]`, `amino[clickhouse]` pulls `clickhouse-connect`. The
backends themselves import neither; only the integration tests do.

### Testing

Unit: table-driven, one row per operator per dialect, asserting exact
`(sql, params)`. Error cases for dotted paths and custom operators.

Integration: a fixed table of ~12 rows covering ints, floats, strings,
bools and a custom-typed email column. A list of ~20 DSL expressions. For
each expression: `SELECT id FROM t WHERE <sql>` on both databases, and the
Python evaluator over the same rows in memory. Assert the three id sets are
equal. Ports 55432 and 58123 avoid the Homebrew Postgres on 5432.

`make db-up`, `make db-down`, `make test-integration` wrap Docker. Plain
`make test` stays database-free.
