# ADR 005: One Language for User-Written Conditions

**Date**: 2026-09-05
**Status**: Accepted
**Supersedes**: the framing in ADR 001 ("schema-first classification rules engine"). Reaffirms ADR 002 decisions 1 through 5.

## Context

Amino has been described three ways since 2021: "a framework to build custom domain specific languages" (first commit), "a toolkit and DSL for custom rules engines" (2022), and "a schema-first classification rules engine" (2026 rewrite). None of those is wrong, but none says what the thing is *for*, and a README written against the third one demonstrated a little of each with mixed results.

The project has no external users. The concrete use cases in view are a query language at the maintainer's workplace, composed on the front end, validated there, and dispatched to whichever store holds the data, and a recurring need for end-user-editable rules. Asking what else has that shape produced a longer list: feature targeting, row-level policy, alert conditions, data quality checks, routing. They all reduce to the same thing.

This ADR records the alignment reached on 2026-09-05 about what amino is for, and what that purpose requires of it.

## Decision

> Amino is a small expression language for building features in which users write conditions over a developer's data: rules engines, query languages, targeting, policy, alerting, and whatever else has that shape.

Amino is not the feature. It is the language layer under the feature, built once so the feature on top can be small. Everything else in this document is a requirement that purpose imposes.

### The features are one shape

Every one of these comes down to a condition, written by someone who is not the developer, over records the developer controls:

| Feature | What the user writes | Where it runs |
|---|---|---|
| Rules engine | `credit_score < 500`, fifty of them, with priorities | In process, every record, batch, with match modes |
| Query language, saved search | `status = 'open' and assignee = ''` | Pushed down to whichever store holds the data |
| Feature targeting, segmentation | `country = 'US' and plan in ['pro', 'team']` | In process to serve the flag; SQL to count the audience |
| Row-level policy | `resource.owner = principal.id or principal.role = 'admin'` | In process for one allow/deny; as a `WHERE` so a list returns only permitted rows |
| Alerting, event triggers | `cpu > 90 and region = 'eu-west'` | Per event as it arrives; as a query over history |
| Data quality | `email contains '@' and age >= 0` | On ingest; as SQL to find existing violations |
| Routing | `amount > 10000 or country != 'US'` | In process, first match wins |
| Pipeline filters, CI conditions | `event_type in ['click', 'view'] and not bot` | Compiled per stage, or once |

Building each of these means building a small condition language, and each is usually built under deadline, slightly differently, and never quite finished. Amino is that language, once.

Adjacent and served by the same machinery: formulas (`price * qty * (1 - discount)`) and scoring (weighted sums of predicates), where the result is a number rather than a boolean. The parser does not care what type the root is.

### Rules and queries are one expression, two directions

The project carried a "rules engine or DSL toolkit?" question for four years. It dissolves here. A **rule** holds the expression fixed and streams records past it: fifty rules, a million records, each record gets a verdict. A **query** holds the dataset fixed and pushes one expression into it: one expression, a million records, the matching subset comes back. The same text is either, depending on which side is the constant. The distinction lives in the target layer, not the grammar. The rules engine is one target.

## Requirements the purpose imposes

Five, each a commitment, in the order they matter for building a feature.

### 1. One fixed grammar

Amino is one language, not a kit for building grammars. The developer supplies **vocabulary** through the schema (fields, structs, custom types, functions, custom operators) but not **syntax**. Comparisons, boolean connectives, membership, substring search, function calls, dot paths, and single-quoted strings are fixed.

**Why**: Features share the language only if the language is the same across them. A user who learns it in the search box knows it in the rules editor. It is also what makes a second host implementation feasible for one maintainer and what makes the safety requirement provable: a closed grammar has a finite list of things it can emit.

**Consequence**: The PEG files in `docs/grammar/` are the specification, not documentation. Changing them is a language change and must land in every host.

### 2. Vocabulary from a developer-defined schema

The schema is the contract, in the same sense as a GraphQL schema: the developer decides what the language can say about their data. It declares fields and types, structs, constraints, custom types (a name, a base primitive, a validator), function signatures, and custom operator signatures.

**Why**: The feature's data model is what users are writing conditions over. The schema is that data model, stated once, and it is what makes an expression checkable before it runs and portable between targets.

**Consequence**: The schema must be exportable in a stable, machine-readable form carrying all of that, including operator signatures, so a host that cannot execute a custom operator can still type-check it. This is ADR 002 decision 5, reaffirmed and widened.

### 3. Compiles to multiple targets

A target consumes a parsed, type-checked expression and produces something executable. Shipping: the in-process Python evaluator (with record validation and match modes), Postgres, ClickHouse. Available to developers: any subclass of `SQLBackend`, or any walker over the typed AST.

**Why**: Half the features in the table need the same expression in both directions. A flag served in process and an audience counted in SQL must agree. A policy that allows one record and a `WHERE` that lists permitted records must agree. "Parse once, compile to many" is the only way to guarantee that.

**Consequence**: An expression must mean the same thing on every target. If two targets can disagree on a supported expression, the feature above them has a bug it cannot see. The parity suite that runs every construct through every target is part of the definition of a target, not a test convenience. Known divergences are defects to close.

### 4. Safe to accept from untrusted users

The users in the table are the feature's end users, not the developer. Sometimes they are employees; sometimes the feature is a text box on the internet. The threat model is the second case: **a developer exposes an endpoint that accepts amino text, and an attacker must not be able to reach arbitrary SQL or arbitrary host-language code through it.**

The guarantees, in one line each; the full statement, what is not covered, deployer responsibilities, and the current implementation status are in [`docs/security.md`](../security.md):

1. The schema is an allowlist. Undeclared names are parse errors.
2. User text never executes. Literals are bound parameters or plain values.
3. Every byte of emitted SQL came from the developer or is a parameter.
4. Every callable invoked in process was registered by the developer.
5. No expression runs unboundedly. No loops, recursion, or definitions; length and depth are capped.
6. An expression means the same thing on every target.

**Why**: Without this, every feature built on amino has to add its own validation layer, and the purpose collapses. With it, exposing the feature to untrusted input is the developer's decision, not a rewrite.

**Status at the time of writing**: guarantees 1, 3, and 5 do not fully hold. The parser accepts undeclared functions and the SQL targets emit them verbatim; there are no length or depth limits; built-in comparisons are not type-checked, so `rules_mode` has no effect and `TypeMismatchError` is never raised. The security document has the reproducing inputs. These are scheduled ahead of new features because they are the class of defect this requirement exists to prevent.

### 5. More than one host implementation

Python is the reference implementation (ADR 002 decision 3). A TypeScript implementation is planned so an expression can be composed and validated in the browser before being sent to a backend (ADR 002 decision 4).

**Why**: The query-language feature needs feedback while the user types. The rules feature benefits from the same. Neither wants a round trip per keystroke.

**Consequences**:

- The backend never trusts the frontend. Browser validation is a user-experience property. The server re-parses and is the only validation that counts for requirement 4.
- Both implementations must accept and reject exactly the same inputs with the same error classes. This needs a shared conformance corpus that every host runs. It does not exist yet.
- Validation rules are named, following GraphQL's spec: "unknown field", "undeclared function", "type mismatch", "depth exceeded", each in the corpus, each mapping to the same error class in every host.
- Custom operators are describable by signature. A host validates `precedes` from its keyword, binding power, and types; only the host that executes it needs the implementation.

## Non-goals

Boundaries, not a backlog. Each is something a feature might want that amino will not provide, because providing it would break one of the requirements above.

- **Sequencing.** Workflows, build steps, state machines. Amino has expressions, not statements. (Requirements 1 and 4.)
- **Shaping output.** Templating, projections, transformations, ordering, pagination, aggregation. Amino says which rows, not what they look like. The `ORDER BY` in a JQL query is the caller's. (Requirements 1 and 3.)
- **Recursion, loops, user-defined functions in the language.** Those belong in the host language behind a schema-declared function. (Requirement 4.)
- **Non-record schemas.** Graph traversals, wildcard document paths, time-series windows. The schema is a flat-ish record with structs. (Requirement 2.)
- **Grammar extension.** (Requirement 1.)
- **Mutation.** Nothing a user writes changes state. (Requirement 4.)

## Comparison with GraphQL

The comparison is worth making precisely because the earlier README reached for it loosely. Both rest on the same bet: **strangers can safely write a language against your data if the schema decides what the language can say.**

### Alike

| | GraphQL | Amino |
|---|---|---|
| Schema is the contract and the allowlist | Server owns it; clients ask only for what it exposes | Developer owns it; users reference only what it exposes |
| Validation is a phase before execution | Parse, validate, execute | Parse, type-check, compile |
| Text is the wire format | Query text travels; every server parses | Expression text travels; every host parses |
| Introspection powers client tooling | `__schema` | Schema export |
| Developer implements behind declared signatures | Resolvers | Functions, custom types, custom operators |
| Custom scalars | `scalar Email` | `email` with base `Str` and a validator |
| Built for untrusted internet input | Depth and complexity limits | Length and depth limits (to be built in) |
| One spec, many implementations, a conformance suite | graphql-js, the spec, shared cases | Python, the PEG grammars, a corpus (to be built) |

### Unlike

- **GraphQL selects shape; amino selects records.** GraphQL is projection. Amino is filtering. GraphQL has no standard `where`, and every server invents a `filter` argument with an ad-hoc mini-language. Amino is a candidate for what goes inside that argument. Adjacent, not competing.
- **GraphQL executes; amino compiles.** GraphQL runs a resolver per field, which is why N+1 exists and why pushing it into SQL took whole products. Amino's targets are the design.
- **GraphQL has side effects; amino has none.** Mutations are half of GraphQL. Amino is read-only by construction.
- **GraphQL is written by developers; amino by end users.** A GraphQL query lives in code and is checked by tooling before it ships. An amino expression is typed into a box at runtime. Lower ceiling on expressiveness, higher floor on error messages.
- **GraphQL is a protocol; amino is a value.** GraphQL is the API. Amino is a string argument to whatever API already exists.
- **GraphQL's spec is hundreds of pages; amino's is two PEG files.** That asymmetry is what makes a second host feasible.

### Take from GraphQL

1. Named validation rules, each in the conformance corpus, same error class in every host.
2. A stable JSON schema export carrying fields, structs, functions, and operator signatures.
3. Limits shipped by default. GraphQL left depth limits to middleware and servers got denial-of-serviced until they were added.
4. Reference implementation plus corpus, so the second implementation stays honest.

### Do not take from GraphQL

- Do not let the `where` language grow into a query language.
- Do not execute per node. Compile.
- Federation, subscriptions, fragments: nothing applies.

A slogan, if one is wanted: *amino is to `WHERE` what GraphQL is to `SELECT`.*

## Consequences

What changes, in rough order:

1. **README and docs** are written around the purpose, with the five requirements as supporting sections. Done alongside this ADR.
2. **Parser** rejects undeclared functions at parse time, rejects mismatched built-in comparisons so that `rules_mode` and `TypeMismatchError` mean something, and enforces default length and depth limits. Closes the gaps under requirement 4.
3. **Named validation rules** and a **conformance corpus** are introduced in the Python implementation first, so the TypeScript implementation has something to be measured against.
4. **Schema export** gains a JSON form that includes operator signatures.
5. **The Python evaluator and matcher move under the targets namespace**, so the rules engine is visibly one target among several.
6. **A TypeScript implementation** of parse and validate, driven by the corpus. Composition and validation in the browser; the backend still re-parses.
7. **Examples** are reworked around the feature table. Two of the three current example apps do not run and all three predate the API.
8. **Documented divergences between targets** (NULL, collation) are reviewed one by one: either made consistent, or made a parse-time error when the schema makes the divergence reachable.

Retired: the sentence in the 2026-09-05 README rewrite that said multi-language plans were abandoned. ADR 002 stands in full.

## Open questions

- Whether comparisons involving optional fields should be a parse-time error on SQL targets, or whether the Python evaluator should adopt three-valued semantics. Either is defensible; leaving them different is not.
- String escaping. The grammar has no way to write a literal containing `'`. Adding it is a language change and must land in every host at once.
- Whether the slogan overclaims. It is accurate about shape and says nothing about purpose, which is the actual point.
