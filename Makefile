# Root Makefile. Host-specific work is delegated to each host's directory.

.PHONY: install-dependencies tidy test test-integration qa db-up db-down

install-dependencies:
	$(MAKE) -C python install-dependencies

tidy:
	$(MAKE) -C python tidy
	cd go && gofmt -l . && go vet ./...
	cd typescript && pnpm typecheck

test: test-python test-go test-ts

.PHONY: test-python test-go test-ts
test-python:
	$(MAKE) -C python test

test-go:
	cd go && go vet ./... && go test ./...

test-ts:
	cd typescript && pnpm install --frozen-lockfile && pnpm typecheck && pnpm test

test-integration: db-up
	$(MAKE) -C python test-integration

qa: tidy test

db-up:
	scripts/dev-db.sh up

db-down:
	scripts/dev-db.sh down
