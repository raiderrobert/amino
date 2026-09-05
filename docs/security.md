# Security Model

The features amino is built for put an expression box in front of the developer's users, and sometimes in front of the open internet. Safety is therefore a requirement of the language, not an add-on for one feature. This document is the reference for what that requirement covers, what it does not, and where the implementation currently falls short of it. It is requirement 4 of [ADR 005](adr/005-one-language-for-user-written-conditions.md) in full.

## Threat model

An attacker controls the full text of an expression. They may submit as many as they like. They know the schema, or can guess it. They must not be able to:

1. Execute SQL other than the predicate amino constructs from the developer's schema.
2. Execute host-language code other than functions the developer registered.
3. Read fields, tables, or functions the developer did not expose.
4. Make a single expression cost more than a small multiple of its length.

Out of scope: an attacker who controls the schema, the column mapping, or the process. Those are the developer's, and amino trusts them completely.

## Guarantees

Each of these must hold in every host implementation and every target.

### 1. The schema is an allowlist

An expression can reference only fields, functions, and operators the developer declared. Anything else is a parse error. Nothing reaches a target unless every identifier in it resolved against the schema.

### 2. User text never executes

There is no `eval`, no template, no string concatenation of user text into anything executable. On SQL targets every literal is a bound parameter. On in-process targets every literal is a plain value.

### 3. Every byte of emitted SQL came from the developer or is a parameter

The SQL a backend produces is assembled from exactly four sources: quoted identifiers from the schema, column fragments from the developer's mapping, operator tokens from a fixed table in the backend, and placeholders. Function names are emitted only when the schema declares the function. There is no fifth source.

Column mapping values are spliced in verbatim. They are trusted fragments written by the developer, and a developer who puts user input into a column mapping has stepped outside the model.

### 4. Every callable invoked in-process was registered by the developer

Operators dispatch to functions from the operator registry. Function calls dispatch to schema-declared functions with developer-supplied implementations. The decision validator runs developer-registered type validators. There is no other path from expression text to a call.

### 5. No expression can run unboundedly

The language has no loops, recursion, assignment, or user-defined functions. An expression's evaluation cost is linear in its length on the Python target and is one predicate on SQL targets. The parser enforces a maximum expression length and a maximum nesting depth so that parsing itself is bounded.

### 6. An expression means the same thing on every target

If two targets can disagree on a supported expression, a user has been handed a footgun they cannot see. The parity suite in `python/tests/integration/` runs every supported construct through Postgres, ClickHouse, and the Python evaluator and requires identical results. Known divergences are listed below and are treated as defects to close, not quirks to document.

## What amino does not guarantee

- **The safety of a function the developer exposes.** If the schema declares `run_report(name: Str) -> Bool` and the implementation shells out, the attacker can shell out. Amino's contract ends at "only declared functions are callable, with arguments of the declared types."
- **The safety of the surrounding query.** A backend produces a predicate. The developer writes the `SELECT` around it. If that `SELECT` reads from a table the user should not see, the predicate cannot help.
- **Authorization.** Amino decides whether an expression is well-formed against a schema, not whether this user may run it. Exposing different schemas to different users is the developer's job and is the intended way to scope what each can reference.
- **Frontend validation.** A TypeScript validator in the browser is a user-experience feature. The server re-parses every expression, and only the server's parse counts.

## Deployer responsibilities

Until the limits in guarantee 5 ship, the deployer should:

- Reject expressions over a length they choose before calling `parse()`. A few kilobytes is generous for any real predicate.
- Run `parse()` under a recursion guard or in a context where `RecursionError` is caught and reported as a bad request.

Always:

- Declare in the schema only the fields and functions this user population should be able to reference. Use separate engines, with separate schemas, for separate trust levels.
- Run the database role that executes backend-produced SQL with the least privilege the query needs. This is defence in depth for guarantee 3, not a substitute for it.
- Treat column mapping values as code. Never derive them from user input.

## Implementation status

### Python (reference implementation)

Probed on 2026-09-05 against the `feat/sql-backends` branch. This table is the honest state and is updated as gaps close.

| Guarantee | Status | Detail |
|---|---|---|
| 1. Schema is an allowlist | **Partial** | Unknown fields are rejected at parse time. Unknown functions are not: the parser accepts any `identifier(...)` and gives it type `Any`. |
| 2. User text never executes | Holds | All literals are parameters on SQL targets and values on the Python target. |
| 3. Emitted SQL is developer-sourced or a parameter | **Does not hold** | Consequence of the gap in guarantee 1. Undeclared function names are emitted verbatim. `pg_sleep(10) = 1`, `pg_read_file('/etc/passwd') contains 'root'`, `version() contains 'PostgreSQL 16'`, and ClickHouse `sleep(3) = 0` all compiled to SQL. |
| 4. Only registered callables run | Holds | The Python target raises on an undeclared function and the rule evaluates false. |
| 5. Bounded cost | **Does not hold** | No length limit. 5,000 nested parentheses raise an uncaught `RecursionError`. |
| 6. Same meaning on every target | **Partial** | 29 expressions agree across three targets. Divergences: SQL three-valued logic on nullable columns versus the Python evaluator's "missing field means false"; database collation versus Python code-point comparison. |

A related gap that is not a security boundary but affects guarantee 6: the parser resolves types and annotates every node, but does not reject a mismatched built-in comparison. `name = 5` on a `Str` field is accepted and evaluates false in Python and false in SQL, so the targets agree, but the user was not told. `rules_mode` is accepted by `load_schema()` and has no effect. See [expression-language.md](expression-language.md#type-checking).

The conformance corpus also found that the parser raises a bare `IndexError` rather than `RuleParseError` when input ends early (an empty expression, `score >`, an unclosed list or call). Not a boundary violation, but a malformed request becomes an unhandled exception instead of a rejection. Recorded as expected failures in `spec/conformance/parse/standard.json`.

Guarantees 1 and 3 close together with one parser change. Guarantee 5 is a depth counter and a length check. Both are scheduled ahead of any new feature.

### Go

The Go host was written against the corpus after the gaps above were known, and enforces all six guarantees: undeclared functions and mismatched built-in comparisons are parse errors, expression length and nesting depth are capped by default (10,000 bytes and 100 levels, configurable), truncated input is a `syntax` error rather than a crash, and custom type validators run during record validation. Its SQL backends produce the same SQL as Python's, verified by tests that assert the exact strings. It has not yet been run through a parity suite against live databases; that is the next step for it.

## Reporting

This is a one-maintainer project without a security contact yet. Open a GitHub issue. If the report is sensitive, say so in the title without details and the maintainer will arrange a channel.
