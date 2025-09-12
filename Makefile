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
	uv run --frozen ruff check --fix-only --show-fixes .

.PHONY: tidy-ty
tidy-ty:
	uv run --frozen ty check .

###########
#  TEST   #
###########

.PHONY: test
test:
	uv run --locked pytest tests --cov-report=term --cov-report=xml --cov-config=pyproject.toml --cov=amino
