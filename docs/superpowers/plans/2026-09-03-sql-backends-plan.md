# Plan: SQL Backends (Postgres, ClickHouse)

Spec: `docs/superpowers/specs/2026-09-03-sql-backends-design.md`

Each task is test-first. Run `uv run pytest tests -q` after each.

1. **Expression + Engine.parse()** — `amino/expression.py`; `Engine.parse()`
   freezes and returns `Expression`. Tests: parse returns typed root, freezes
   engine, `base_type` resolves custom types.
2. **Backend base + errors** — `amino/backends/base.py` with `Query`,
   `SQLBackend` (abstract hooks), tree walk for Literal/Variable/Unary/Binary/
   FunctionCall; `UnsupportedExpressionError` in `amino/errors.py`.
3. **PostgresBackend** — `%s` positional params, `"ident"` quoting,
   `= ANY(%s)` for lists, `position(x IN y) > 0` for contains. Table-driven
   unit tests for every standard operator, column mapping, error cases.
4. **ClickHouseBackend** — `{pN:Type}` named params, backtick quoting,
   `IN {pN:Array(T)}`, `position(hay, needle) > 0`. Same test table.
5. **Docker + integration harness** — `docker-compose.yml`, Makefile targets,
   optional extras in `pyproject.toml`, `tests/integration/conftest.py` that
   connects or skips, seeds one table per database.
6. **Parity tests** — `tests/integration/test_sql_parity.py`: ~20
   expressions, assert Postgres == ClickHouse == Python evaluator id sets.
7. **Docs** — README section "Compile targets", `docs/backends.md`, update
   `docs/README.md` index. Note the follow-ups from the spec.
8. **QA + PR** — ruff check, ruff format --check, ty, pytest; conventional
   commits; open PR.
