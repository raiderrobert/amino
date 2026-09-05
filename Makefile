# Root Makefile. Host-specific work is delegated to each host's directory.
# Today only python/ exists; typescript/ and go/ targets are added when those hosts land.

.PHONY: install-dependencies tidy test test-integration qa db-up db-down

install-dependencies:
	$(MAKE) -C python install-dependencies

tidy:
	$(MAKE) -C python tidy

test:
	$(MAKE) -C python test

test-integration: db-up
	$(MAKE) -C python test-integration

qa: tidy test

db-up:
	scripts/dev-db.sh up

db-down:
	scripts/dev-db.sh down
