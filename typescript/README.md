# amino for TypeScript

Not started. This directory reserves the place for the TypeScript host implementation described in [ADR 002](../docs/adr/002-dsl-interchange-format-and-multi-language.md) and requirement 5 of [ADR 005](../docs/adr/005-one-language-for-user-written-conditions.md).

## What it is for

Composing and validating an expression in the browser before it is sent to a backend, so the user gets feedback as they type without a round trip. The backend still re-parses. Browser validation is a convenience, not a security boundary.

## The contract

A conforming implementation:

1. Implements the grammars in [`../spec/grammar/`](../spec/grammar/) exactly. No extensions, no relaxations.
2. Passes every case in [`../spec/conformance/`](../spec/conformance/), mapping each named validation rule to its own error type.
3. Type-checks against a schema obtained from the reference implementation's export. Custom operators are validated from their signature alone; only the host that executes them needs the implementation.
4. Ships no evaluator or compile target until the parse and validate layer passes the corpus. Targets are a separate decision.

## Expected shape

- `pnpm` for the package, `vitest` for tests, one package at this directory's root.
- A corpus runner that reads `../spec/conformance/**/*.json` directly, so the corpus is never copied.
- Zero runtime dependencies. A parser for a two-file grammar should not need any.
