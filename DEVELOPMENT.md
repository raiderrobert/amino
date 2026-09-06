# Development

One repository, one language, several hosts. [ADR 006](docs/adr/006-repository-layout-for-multiple-hosts.md) explains the layout.

```
spec/           what every host must implement: grammar/ (PEG) and conformance/ (JSON corpus)
docs/           language-agnostic docs and ADRs; docs/README.md orders them
python/         reference implementation; its own README, API.md, tests, and toolchain
typescript/     parse, validate, and evaluate for the browser and Node; no SQL targets
go/             full runtime for services: parse, validate, evaluate, Postgres and ClickHouse targets
scripts/        shared tooling: dev-db.sh starts the databases every host's parity suite uses
```

## Working on a host

Toolchains: Python 3.10 or newer with `uv`; Go 1.22 or newer; Node 18 or newer with `pnpm`; Docker for the SQL parity suite.

Each host directory is self-contained and uses its own toolchain. For Python:

```bash
cd python
uv sync --all-extras
uv run pytest tests                      # unit tests and the conformance corpus
uv run ruff check && uv run ruff format --check
uv run ty check amino
```

For Go:

```bash
cd go
go test ./...                            # unit tests and the conformance corpus
go vet ./... && gofmt -l .
```

For TypeScript:

```bash
cd typescript
pnpm install
pnpm typecheck && pnpm build && pnpm test   # tests include the conformance corpus
```

The root `Makefile` delegates to the hosts that exist:

```bash
make test               # every host's tests; integration tests skip without databases
make tidy
make db-up              # postgres:16 on :55432, clickhouse:24.8 on :18123, via Docker
make test-integration   # SQL parity suites against live databases
make db-down
```

Ports are non-default to avoid a local Postgres on 5432. Override with `AMINO_PG_PORT` and `AMINO_CH_PORT` for the script, and `AMINO_PG_DSN` and `AMINO_CH_URL` for the tests.

## Working on the language

The grammar and the corpus are the specification. A change to what the language accepts is not a Python change, a TypeScript change, or a Go change; it is a language change, and it lands in this order:

1. Add cases to `spec/conformance/` that fail on the old behaviour. If no host implements the new behaviour yet, mark them `xfail` with a reason.
2. Update `spec/grammar/` if the syntax changed.
3. Update every host that exists, and remove the `xfail` markers as each passes.
4. Update the language docs in `docs/`.

Named validation rules are listed in `spec/conformance/README.md`. A new kind of rejection gets a name there before it gets an error class anywhere.

## Conventions

- Conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, `chore:`. Prefix host-specific work with the host when it helps: `feat(python):`, `feat(go):`.
- Every new target goes into a parity suite and runs the eval half of the corpus. A target that can disagree with the others on a supported expression is a defect.
- A change that affects a guarantee in `docs/security.md` updates the status table there in the same pull request.
- Python: line length 120, type hints on public signatures. The Python tree predates consistent formatting, so `ruff format --check` fails on files you did not touch; format what you change and leave the rest.

## Releases

No host is published yet. Each host will version independently on its own registry once it has a first release; the language itself is versioned by the corpus.
