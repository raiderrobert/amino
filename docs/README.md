# Amino Documentation

Amino is a small, fixed expression language that is safe to accept from untrusted users. Its vocabulary comes from a developer-defined schema. It compiles to multiple targets, and it will have more than one host implementation.

The documents below are ordered so that reading them top to bottom is a sensible path.

## Read first

| Document | What it answers |
|---|---|
| [ADR 005: A Safe Expression Language for Untrusted Users](adr/005-safe-expression-language-for-untrusted-users.md) | What amino is, why it is shaped this way, what it refuses to be, and how it compares to GraphQL. |
| [security.md](security.md) | The threat model, the six guarantees, what is not guaranteed, deployer responsibilities, and the current implementation status. |
| [architecture.md](architecture.md) | The pipeline from schema text to a target, the engine lifecycle, and the package layout. |

## Language reference

| Document | Covers |
|---|---|
| [schema-language.md](schema-language.md) | Fields, primitives, lists, optional fields, constraints, structs, functions, custom types, export. |
| [expression-language.md](expression-language.md) | Atoms, operators and binding powers, presets, custom operators, what type checking does and does not do, what is deliberately absent. |
| [grammar/](grammar/) | The formal PEG grammars. These are the specification every host implementation must match. |

## Running expressions

| Document | Covers |
|---|---|
| [targets.md](targets.md) | The Python evaluator (compile, eval, match modes, decision validation), Postgres, ClickHouse, shared SQL behaviour, known divergences, and writing a target. |
| [api.md](api.md) | Every public function, class, and error. |

## Decision records

`adr/` holds the reasoning behind each major decision. Earlier ADRs are written in rules-engine vocabulary; ADR 005 reframes the project and notes how each earlier decision reads under the new framing.

| ADR | Title |
|---|---|
| [001](adr/001-engine-architecture-and-lifecycle.md) | Engine Architecture, Lifecycle, and Type Enforcement |
| [002](adr/002-dsl-interchange-format-and-multi-language.md) | DSL as Interchange Format and Multi-Language Strategy |
| [003](adr/003-extensibility-model.md) | Extensibility Model |
| [004](adr/004-schema-language-features.md) | Schema Language Features |
| [005](adr/005-safe-expression-language-for-untrusted-users.md) | A Safe Expression Language for Untrusted Users |
