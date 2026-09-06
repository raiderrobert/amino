# Root justfile. Host-specific work is delegated to each host's directory.
# `just --list` shows every recipe; `just python::<recipe>` runs one host's recipe directly.

mod python

# List the available recipes.
default:
    @just --list

# Install every host's dependencies.
install-dependencies: python::install-dependencies

# Format and type-check every host.
tidy: python::tidy tidy-go tidy-ts

tidy-go:
    cd go && gofmt -l . && go vet ./...

tidy-ts:
    cd typescript && pnpm typecheck

# Run every host's tests. Integration tests skip when the databases are down.
test: test-python test-go test-ts

test-python: python::test

test-go:
    cd go && go vet ./... && go test ./...

test-ts:
    cd typescript && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test

# Run the SQL parity suites against live Postgres and ClickHouse.
test-integration: python::test-integration

# Tidy, then test.
qa: tidy test

# Start Postgres and ClickHouse in Docker (idempotent).
db-up:
    scripts/dev-db.sh up

# Stop and remove the Docker databases.
db-down:
    scripts/dev-db.sh down
