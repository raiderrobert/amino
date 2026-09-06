# Root Makefile. Host-specific work is delegated to each host's directory.
# typescript/ targets are added when that host lands.

.PHONY: install-dependencies tidy test test-integration qa db-up db-down

install-dependencies:
	$(MAKE) -C python install-dependencies

tidy:
	$(MAKE) -C python tidy
	cd go && gofmt -l . && go vet ./...

test: test-python test-go

.PHONY: test-python test-go
test-python:
	$(MAKE) -C python test

test-go:
	cd go && go vet ./... && go test ./...

test-integration: db-up
	$(MAKE) -C python test-integration

qa: tidy test

db-up:
	scripts/dev-db.sh up

db-down:
	scripts/dev-db.sh down
