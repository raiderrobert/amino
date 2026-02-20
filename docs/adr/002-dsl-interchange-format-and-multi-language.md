# ADR 002: DSL as Interchange Format and Multi-Language Strategy

**Date**: 2026-02-18
**Status**: Accepted

## Context

Amino needs to be usable across multiple languages and services. Rules need to be portable — storable in databases, transmitted over the wire, and evaluated by different systems. This requires a decision about what the portable artifact is: the DSL text, a serialized AST, or a language-agnostic IR.

Additionally, a multi-language implementation strategy is needed. Amino should be accessible from languages beyond Python without requiring a full engine rewrite in each language from the start.

## Decisions

### 1. DSL text is the interchange format

The rule DSL (text strings) is the portable artifact — not a serialized AST, not a JSON IR, not a binary format. Rules travel across the wire and are stored in databases as DSL text. Each runtime implementation parses and compiles the DSL independently.

**Rationale**: DSL text is language-agnostic, human-readable, and versionable. Serializing an AST would couple all implementations to a shared IR schema, creating coordination overhead and making independent language implementations harder. This is the same bet Cedar made — their policy language is the interchange format, with independent implementations in Rust, Go, Java, and others.

**Consequence**: Every runtime implementation must include a parser and compiler. Client-side SDKs that don't implement a full runtime produce DSL text to be evaluated by a runtime elsewhere.

### 2. The portable unit is (schema + DSL), not DSL alone

Since rules are type-checked against the schema at compile time, a rule string is only meaningful in the context of a schema. The portable unit for a rule is the (schema, DSL text) pair, not the DSL text in isolation.

**Rationale**: A rule referencing `credit_score < 600` has no meaning without knowing that `credit_score` is an `Int` field. Services that receive and compile rules must also have access to the schema. This connects to the decision context concept from ADR 001.

### 3. Python is the initial reference implementation

Python is the first full implementation of the amino runtime: parser, type checker, compiler, and evaluator. It is the reference implementation against which other language implementations should be validated.

**Rationale**: Python has a large install base in the decisioning use cases amino targets — ML pipelines, fintech, data engineering, risk scoring. It is also the language the author knows best, making it the right place to establish correct behavior.

**Consequence**: Python correctness is the baseline. Future implementations in other languages must produce identical results for identical (schema, rule, decision) inputs.

### 4. Other language SDKs start as rule composers

Before full runtime implementations exist in other languages, SDKs for those languages (TypeScript first) will be rule composers: libraries that help users write and validate DSL text without implementing a full parser and evaluator.

A rule composer may optionally fetch the schema from a running amino instance and perform client-side preflight validation, giving fast feedback without round-tripping to the runtime.

**Rationale**: A full runtime implementation in every language from day one is unnecessary. Composition SDKs provide value immediately (type-safe rule building, editor tooling) while the reference implementation matures.

**Consequence**: The composer/runtime split is temporary. The goal is independent full implementations over time, following the Cedar model.

### 5. Schema introspection is a first-class operation

Amino must support exporting the current schema in a stable, language-agnostic format. This enables client SDKs to fetch the schema and perform local preflight validation before submitting rules to a runtime.

**Rationale**: Preflight validation (client-side, using the schema) provides fast feedback in development without replacing server-side compilation as the authoritative gate. This mirrors GraphQL's introspection model: the schema is authoritative on the server, but clients can pull it down for local tooling.

**Consequence**: The schema format must be serializable. Preflight is a courtesy; server-side (runtime) compilation remains the authoritative validation gate.

## Consequences

- Rules are stored and transmitted as text — portable, human-readable, and diffable.
- Every future runtime implementation needs a parser and compiler, not just a deserializer.
- Python correctness is the specification for all other implementations.
- Client SDKs can provide preflight validation without a full runtime.
- Schema must be exportable in a stable format.

## Open Questions

- What is the stable serialization format for schema export (the amino schema file format itself, JSON, or something else)?
- How does a client SDK discover the schema — HTTP endpoint, file, environment variable?
- What does the preflight validation API look like in a composer SDK?
