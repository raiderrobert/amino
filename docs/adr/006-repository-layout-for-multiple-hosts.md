# ADR 006: Repository Layout for Multiple Hosts

**Date**: 2026-09-06
**Status**: Accepted

## Context

ADR 005 requirement 5 commits amino to more than one host implementation: Python as the reference, TypeScript for composing and validating in the browser, and Go for services. Until now the repository was the Python package, with the grammars filed under `docs/`. A second implementation would have had nowhere to sit that did not read as an add-on to the first, and nothing shared to be measured against except the Python code itself.

## Decisions

### 1. One repository, hosts as sibling directories

```
python/       reference implementation; package, tests, examples, its own README and API.md
typescript/   browser-side parse and validate; placeholder until started
go/           full runtime for services; placeholder until started
spec/         what every host must implement: grammar/ and conformance/
docs/         language-agnostic: ADRs, security model, architecture, language references, targets
scripts/      shared tooling, today the local database script used by every host's parity suite
```

**Why one repository**: the grammar, the corpus, and the docs change together with the implementations, and a language change is not complete until every host has landed it. Separate repositories would make that a coordination problem. One repository makes it one pull request.

**Why siblings**: a layout with Python at the root and others beside it says Python is the product and the rest are ports. ADR 005 says the language is the product and every host is an implementation of it.

### 2. `spec/` is the specification

`spec/grammar/` holds the PEG grammars, moved from `docs/grammar/`. `spec/conformance/` holds a corpus of parse and eval cases in JSON, self-contained per file, that every host must pass. The corpus format and the named validation rules are defined in `spec/conformance/README.md`.

**Why a corpus and not just the reference implementation**: "produce identical results to Python" is not something a Go developer can run in CI. A JSON corpus is. It also lets the specification lead the implementation: a case the reference implementation fails carries an `xfail` and describes required behaviour that no host has yet.

**Consequence**: adding a case to the corpus is how a language change starts. Named validation rules replace "whatever `RuleParseError` says" as the contract between hosts.

### 3. Language-agnostic docs stay at the root; host-specific docs move into the host

`docs/` describes the language, the security model, the targets as concepts, and the decisions. Anything that is an API reference for one host lives with that host: `python/API.md` today. Each host directory has a README that states the contract it must meet and how to run its tests.

### 4. Root tooling delegates

The root `Makefile` delegates `test`, `tidy`, `test-integration` to each host directory and owns only what is shared (`db-up`, `db-down`). Each host keeps its own build tool: `uv` for Python, `pnpm` for TypeScript, `go` for Go.

### 5. Install paths change once

The Python package installs from git with `#subdirectory=python`. This is the one user-visible cost of the layout and it is paid now, before there are users to pay it.

## Consequences

- The Python package moves under `python/` with its `pyproject.toml`, lockfile, tests, and examples. Tests pass unchanged.
- Every link to `docs/grammar/` and `docs/api.md` is updated.
- A conformance runner is added to the Python tests so the corpus is exercised from day one, and the cases the reference implementation is known to fail are recorded as expected failures rather than omitted.
- TypeScript and Go directories contain only a README until their implementations start. Nothing half-built ships.
- CI, when it exists, runs each host's tests from its own directory.

## Open Questions

- Whether the eval corpus should also drive the SQL parity suite directly, replacing the expression list in `python/tests/integration/test_sql_parity.py`. Probably yes; deferred so this change stays a move.
- A JSON schema export (ADR 005 consequence 4) will need a place in `spec/` for its format definition.
