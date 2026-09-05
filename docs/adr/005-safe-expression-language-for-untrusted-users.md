# ADR 005: A Safe Expression Language for Untrusted Users

**Date**: 2026-09-05
**Status**: Accepted
**Supersedes**: the framing in ADR 001 ("schema-first classification rules engine"). Reaffirms ADR 002 decisions 1 through 5.

## Context

Amino has been described three ways since 2021: "a framework to build custom domain specific languages" (first commit), "a toolkit and DSL for custom rules engines" (2022), and "a schema-first classification rules engine" (2026 rewrite). None of those descriptions is wrong, but none of them says what the thing is *for*, and the README written against the third one demonstrated a little of each with mixed results.

The project has no external users. The one concrete use case in view is a query language at the maintainer's workplace: end users compose a search on the front end, it is validated there, sent to a backend, and dispatched to whichever store holds the data. The maintainer also keeps encountering the need for end-user-editable rules and does not want to lose that.

This ADR records the alignment reached on 2026-09-05 about what amino is, what it guarantees, and what it refuses to be.

## Decision

> Amino is a small, fixed expression language that is safe to accept from untrusted users. Its vocabulary comes from a developer-defined schema. It compiles to multiple targets, and it has more than one host implementation.

Each clause is a commitment.

### One fixed grammar

Amino is one language, not a kit for building grammars. The developer supplies **vocabulary** (fields, structs, custom types, functions, custom operators) but not **syntax**. Comparisons, boolean connectives, membership, substring search, function calls, dot paths, and single-quoted strings are fixed.

**Why**: Every syntax extension would have to be implemented in every host (see "more than one host implementation"). A fixed grammar is what makes a second implementation feasible for one maintainer. It is also what makes the safety guarantees provable: a closed grammar has a finite list of things it can emit.

**Consequence**: The PEG files in `docs/grammar/` are the specification, not documentation. Changes to them are language changes and need a corresponding change in every host.

### Safe to accept from untrusted users

The threat model is concrete: **a developer exposes an endpoint to the internet that accepts amino text, and an attacker must not be able to reach arbitrary SQL or arbitrary host-language code through it.**

"Safe" is a runtime property about the system, not a usability property about the author. Good error messages and authoring tools matter, but they are downstream of this.

The guarantees, each of which must hold in every host and every target:

1. **The schema is an allowlist.** An expression can reference only fields, functions, and operators the developer declared. Anything else is rejected at parse time, before any target sees it.
2. **User text never executes.** No `eval`, no string interpolation. Every literal the user types is bound as a parameter on SQL targets and is a plain value on in-process targets.
3. **Every byte of emitted SQL came from the developer or is a bound parameter.** Identifiers come from the schema, column fragments and function names come from the developer's declarations, operators come from a fixed table, and everything else is a placeholder.
4. **Every callable invoked in-process was registered by the developer.** Operators dispatch to registered functions. Function calls dispatch to schema-declared functions with developer-supplied implementations. There is no other path to code.
5. **No expression can run unboundedly.** The language has no loops, recursion, or definitions. Cost is proportional to expression length. The parser enforces a maximum length and nesting depth by default.
6. **An expression means the same thing on every target.** If the Python evaluator and the Postgres backend can disagree on a supported expression, the user has been handed a footgun they cannot see. The parity suite is a safety property, not a test convenience. Known divergences (NULL semantics, collation) are documented and are candidates for being made errors rather than surprises.

**What amino cannot guarantee**: the safety of a function the developer chose to expose. If the schema declares `run_report(name: Str) -> Bool` and the implementation shells out, that is the developer's exposure. Amino's contract ends at "only declared functions are callable."

#### Status of the guarantees at the time of writing

Probed on 2026-09-05 against `feat/sql-backends`:

| Guarantee | Python target | Postgres / ClickHouse targets |
|---|---|---|
| 1. Schema is an allowlist | Fields: yes. **Functions: no.** The parser accepts any `identifier(...)` and assigns type `Any` if undeclared. | Same parser, so same gap. |
| 2. User text never executes | Yes | Yes. All literals bound. |
| 3. Emitted SQL is developer-sourced or a parameter | n/a | **No.** Undeclared function names are emitted verbatim. `pg_sleep(10) = 1`, `pg_read_file('/etc/passwd') contains 'root'`, `version() contains 'PostgreSQL 16'`, and ClickHouse `sleep(3) = 0` all compiled. |
| 4. Only registered callables run | Yes. Undeclared functions raise at evaluation and the rule evaluates false. | n/a |
| 5. Bounded cost | **No.** 5,000 nested parentheses raise an uncaught `RecursionError`. No length limit. | Same. |
| 6. Same meaning everywhere | 29 expressions agree across all three. NULL and collation divergences documented. | Same. |

Guarantees 1 and 3 have the same root cause and the same fix: the parser rejects undeclared functions. Guarantee 5 is a depth counter and a length check in the parser. Both are small. Both are recorded here because this is the class of bug the framing exists to prevent, and the README should state the guarantees rather than a changelog stating the fixes.

### Vocabulary from a developer-defined schema

The schema is the contract, in the same sense as a GraphQL schema: the developer decides what the language can say about their data, and safety follows from that decision. It declares fields and their types, structs, constraints, custom types (a name, a base primitive, a validator), function signatures, and custom operator signatures.

**Consequence**: The schema must be exportable in a stable, machine-readable form that carries *all* of that, including operator signatures, so that a host which cannot execute a custom operator can still type-check it. This is ADR 002 decision 5, reaffirmed and widened.

### Compiles to multiple targets

A target consumes a parsed, type-checked expression and produces something executable. Targets that exist: the in-process Python evaluator (with decision validation and match modes), Postgres, ClickHouse. Targets a developer can write: any subclass of `SQLBackend`, or any walker over the typed AST.

**Rules and queries are not two languages.** They are two directions of applying one expression:

- A **rule** holds the expression fixed and streams records past it. Fifty rules, a million records, each record gets a verdict. In-process, batch, with match modes.
- A **query** holds the dataset fixed and pushes one expression into it. One expression, a million records, the matching subset comes back. Compiled to the store's language.

The same text is either, depending on which side is the constant. The distinction lives in the target layer, not the grammar. This dissolves the "rules engine vs. DSL toolkit" question the project has carried since 2022: the rules engine is one target.

### More than one host implementation

Python is the reference implementation (ADR 002 decision 3). A TypeScript implementation is planned so that an expression can be composed and validated in the browser before being sent to a backend (ADR 002 decision 4).

Hard constraints this imposes:

- **The backend never trusts the frontend.** Browser validation is a user-experience property. The server re-parses and is the only validation that counts for the threat model.
- **Both implementations must accept and reject exactly the same inputs**, with the same error classes. This requires a shared conformance corpus of expressions, schemas, and expected outcomes that every host runs. It does not exist yet.
- **Validation rules are named.** Following GraphQL's spec, each rule ("unknown field", "undeclared function", "type mismatch", "depth exceeded", and so on) has a name, appears in the corpus, and maps to the same error class in every host.
- **Custom operators are describable by signature.** A host validates `precedes` from its keyword, binding power, and input/output types. Only the host that executes it needs the implementation.

## Use cases

Amino fits wherever an untrusted person needs to express a condition over records the developer controls. The cases with the most pull are the ones that need the **same expression in both directions**: decide for one record now, and select every matching record later.

| Use case | What the user writes | Where it runs |
|---|---|---|
| Audience segmentation, feature-flag targeting | `country = 'US' and plan in ['pro', 'team']` | In-process to serve the flag; SQL to count or export the audience |
| Authorization, row-level policy | `resource.owner = principal.id or principal.role = 'admin'` | In-process for one allow/deny; as a `WHERE` so a list endpoint returns only permitted rows |
| Alerting, event triggers | `cpu > 90 and region = 'eu-west'` | Per event as it arrives; as a query over history |
| Data quality checks | `email contains '@' and age >= 0` | On ingest; as SQL to find existing violations |
| Routing, dispatch | `amount > 10000 or country != 'US'` | In-process, first match wins |
| Search and filter UI (the JQL shape) | `status = 'open' and assignee = ''` | Pushed down to whichever store holds the data |
| Pipeline filters | `event_type in ['click', 'view'] and not bot` | Compiled per stage |
| CI and config conditions | `branch = 'main' and not draft` | In-process, once |

Adjacent, same machinery, non-boolean result: formulas (`price * qty * (1 - discount)`) and scoring (weighted sums of predicates). The parser does not care what type the root is; `score` match mode already uses this.

## Non-goals

These are boundaries, not a backlog.

- **Sequencing.** Workflows, build steps, state machines. Amino has expressions, not statements.
- **Shaping output.** Templating, projections, transformations, ordering, pagination, aggregation. Amino says which rows, not what they look like. The `ORDER BY` in a JQL query is the caller's, not amino's.
- **Recursion, loops, user-defined functions in the language.** Those belong in the host language behind a schema-declared function.
- **Non-record schemas.** Graph traversals, wildcard document paths, time-series windows. The schema is a flat-ish record with structs.
- **Grammar extension.** See "one fixed grammar."
- **Mutation.** Nothing a user writes changes state.

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

- **GraphQL selects shape; amino selects records.** GraphQL is projection. Amino is filtering. GraphQL has no standard `where`, and every server invents a `filter` argument with an ad-hoc mini-language. Amino is a candidate for what goes inside that argument. They are adjacent, not competing.
- **GraphQL executes; amino compiles.** GraphQL runs a resolver per field, which is why N+1 exists and why pushing it into SQL took whole products. Amino's targets are the design.
- **GraphQL has side effects; amino has none.** Mutations are half of GraphQL. Amino is read-only by construction, which is a large part of why "safe" fits in two grammar files.
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

1. **README** is rewritten around this ADR. It states the guarantees, the threat model, the non-goals, and the GraphQL comparison. It does not lead with rules or with queries.
2. **Parser** rejects undeclared functions at parse time and enforces default length and depth limits. Closes the gaps in the status table above.
3. **Named validation rules** and a **conformance corpus** are introduced in the Python implementation first, so the TypeScript implementation has something to be measured against.
4. **Schema export** gains a JSON form that includes operator signatures.
5. **The Python evaluator and matcher move under the targets namespace**, so the rules engine is visibly one target among several.
6. **A TypeScript implementation** of parse and validate, driven by the corpus. Composition and validation in the browser; the backend still re-parses.
7. **Examples** are reworked around the use-case table. Two of the three current example apps do not run and all three predate the API.
8. **Documented divergences between targets** (NULL, collation) are reviewed one by one: either made consistent, or made a parse-time error when the schema makes the divergence reachable (for example, comparing an optional field on a SQL target).

Retired: the sentence in the 2026-09-05 README rewrite that said multi-language plans were abandoned. ADR 002 stands in full.

## Open questions

- Whether comparisons involving optional fields should be a parse-time error on SQL targets, or whether the Python evaluator should adopt three-valued semantics. Either is defensible; leaving them different is not.
- String escaping. The grammar has no way to write a literal containing `'`. Adding it is a language change and must land in every host at once.
- Whether the slogan overclaims. It is accurate about shape and says nothing about safety, which is the actual point.
