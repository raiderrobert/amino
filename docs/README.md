# Amino Documentation

Amino is a toolkit for building a small, typed expression language over your data and compiling it to more than one target. The schema defines the type system. Expressions are parsed and type-checked against it once. A target then turns the typed expression into something executable: an in-process Python evaluator with match modes (the original rules engine), a Postgres or ClickHouse `WHERE` predicate, or a backend you write.

## Documents

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | System design: pipeline, data groups, engine lifecycle, multi-language strategy, error hierarchy, and file structure |
| [schema-language.md](schema-language.md) | Reference for the `.amn` schema language: primitives, complex types, optional fields, constraints, structs, function declarations, and custom types |
| [rule-expression.md](rule-expression.md) | Reference for the rule expression language: atoms, operator system, presets, match modes, and custom operator registration |
| [api.md](api.md) | Public API reference: `load_schema()`, registration methods, evaluation methods, and result types |
| [backends.md](backends.md) | Compile targets: `engine.parse()`, the Postgres and ClickHouse SQL backends, column mapping, and the parity test suite |
| [grammar/](grammar/) | Formal PEG grammars for the schema language (`schema.peg`) and rule expression language (`rules.peg`) |
| [adr/](adr/) | Architecture Decision Records — the why behind each major design decision |

## Architecture Decision Records

The `adr/` directory contains the decisions made during the design of the rewrite. Each ADR captures the context, the decision, and the consequences. They are the authoritative record of why the system is designed the way it is, not just what it does.

| ADR | Title |
|-----|-------|
| [001](adr/001-engine-architecture-and-lifecycle.md) | Engine Architecture, Lifecycle, and Type Enforcement |
| [002](adr/002-dsl-interchange-format-and-multi-language.md) | DSL as Interchange Format and Multi-Language Strategy |
| [003](adr/003-extensibility-model.md) | Extensibility Model |
| [004](adr/004-schema-language-features.md) | Schema Language Features |
