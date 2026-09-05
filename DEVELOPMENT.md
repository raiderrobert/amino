# Development

## Setup

Python 3.10 or newer, `uv`, and Docker if you want to run the SQL parity suite.

```bash
git clone https://github.com/raiderrobert/amino.git
cd amino
make install-dependencies
```

## Layout

```
amino/            the package; see docs/architecture.md for what lives where
tests/            unit tests, no external services
tests/integration/ parity suite against Postgres and ClickHouse; skips when they are down
docs/             reference docs and ADRs; docs/README.md orders them
examples/         predate the current API and do not run; being reworked
scripts/dev-db.sh starts and stops the local databases with plain docker run
```

## Checks

```bash
make tidy               # ruff format, ty check
make test               # pytest tests/ with coverage; integration tests skip without databases
make db-up              # postgres:16 on :55432, clickhouse:24.8 on :18123
make test-integration   # the parity suite against live databases
make db-down
```

Before a pull request: `uv run ruff check`, `uv run ruff format --check`, `uv run ty check amino`, `uv run pytest tests`. The repository predates consistent formatting, so `ruff format --check` fails on files you did not touch. Format the files you changed and leave the rest.

The databases use non-default ports so they do not collide with a local Postgres on 5432. Override with `AMINO_PG_PORT` and `AMINO_CH_PORT` for the script, and `AMINO_PG_DSN` and `AMINO_CH_URL` for the tests.

## Conventions

- Conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- Every change to the grammar or to what the parser accepts is a language change. It needs a corresponding change in every host implementation and a case in the conformance corpus, once that exists.
- Every new target goes into the parity suite. A target that can disagree with the others on a supported expression is a defect.
- A change that affects a guarantee in `docs/security.md` updates the status table there in the same pull request.
- Line length 120. Type hints on public signatures.

## Releases

Not on PyPI yet. Versions will follow semver once there is a first release.
