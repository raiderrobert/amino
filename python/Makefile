###########
# INSTALL #
###########

.PHONY: install-dependencies
install-dependencies:
	@uv sync --all-groups --all-extras

.PHONY: upgrade-dependencies
upgrade-dependencies:
	@uv sync --all-groups --all-extras --upgrade

.PHONY: qa
qa: tidy test

###########
#  TIDY   #
###########

.PHONY: tidy
tidy: tidy-ruff tidy-ty

.PHONY: tidy-ruff
tidy-ruff:
	uv run --frozen ruff format .

.PHONY: tidy-ty
tidy-ty:
	uv run --frozen ty check .

###########
#  TEST   #
###########

.PHONY: test
test:
	uv run --locked pytest tests --cov-report=term --cov-report=xml --cov-config=pyproject.toml --cov=amino

# Runs the SQL parity suite against local Postgres and ClickHouse containers.
# `make test` also runs these but skips them when the databases are down.
.PHONY: test-integration
test-integration: db-up
	uv run --locked pytest tests/integration -v

###########
#   DB    #
###########

.PHONY: db-up
db-up:
	../scripts/dev-db.sh up

.PHONY: db-down
db-down:
	../scripts/dev-db.sh down
