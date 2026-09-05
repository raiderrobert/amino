# amino for Go

Not started. This directory reserves the place for the Go host implementation described in requirement 5 of [ADR 005](../docs/adr/005-one-language-for-user-written-conditions.md).

## What it is for

Evaluating and compiling expressions inside Go services without calling out to Python. Unlike the TypeScript host, whose first job is validation in the browser, a Go host is expected to be a full runtime: parse, validate, evaluate in process, and compile to SQL targets.

## The contract

A conforming implementation:

1. Implements the grammars in [`../spec/grammar/`](../spec/grammar/) exactly. No extensions, no relaxations.
2. Passes every case in [`../spec/conformance/`](../spec/conformance/), both `parse` and `eval`, mapping each named validation rule to its own error type.
3. Produces identical results to the reference implementation for identical (schema, expression, record) inputs. The `eval` corpus is the definition of identical.
4. Adds any SQL target it ships to a parity suite against real databases, the same way `python/tests/integration/` does.

## Expected shape

- Module path `github.com/raiderrobert/amino/go`, one module at this directory's root, standard layout (`internal/` for the parser, a small public package).
- `go test` runs the corpus by reading `../spec/conformance/**/*.json` directly.
- No dependencies beyond the standard library for parse, validate, and evaluate. Database drivers only in the target packages that need them.
