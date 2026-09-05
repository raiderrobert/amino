# amino for Python

The reference implementation. Its behaviour is the specification that other hosts must match, and it is the only host today with an in-process evaluator and SQL targets.

## Install

Not on PyPI yet.

```bash
pip install "git+https://github.com/raiderrobert/amino.git#subdirectory=python"
pip install "amino[postgres] @ git+https://github.com/raiderrobert/amino.git#subdirectory=python"
pip install "amino[clickhouse] @ git+https://github.com/raiderrobert/amino.git#subdirectory=python"
```

Python 3.10 or newer. The database extras are only needed to execute what a SQL target produces; the package imports no driver.

## Use

```python
import amino

engine = amino.load_schema("credit_score: Int\nstate_code: Str")
engine.eval(
    rules=[{"id": "decline", "rule": "credit_score < 600 and state_code in ['CA', 'NY']"}],
    decision={"credit_score": 580, "state_code": "CA"},
).matched   # ['decline']
```

The full public API is in [API.md](API.md). The language, the targets, and the security model are documented for all hosts in [`../docs/`](../docs/README.md).

## Layout

```
amino/            the package; docs/architecture.md describes each module
tests/            unit tests and the conformance runner; no external services
tests/integration/ parity suite against Postgres and ClickHouse; skips when they are down
examples/         predate the current API and do not run; being reworked
```

## Develop

From this directory:

```bash
uv sync --all-extras
uv run pytest tests                      # includes spec/conformance via test_conformance.py
uv run ruff check && uv run ruff format --check
uv run ty check amino
```

Or from the repository root, `make test`, `make tidy`, `make test-integration`, which delegate here. The integration suite needs the databases from `../scripts/dev-db.sh up` (or `make db-up` at the root).
