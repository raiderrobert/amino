# ADR 001: Engine Architecture, Lifecycle, and Type Enforcement

**Date**: 2026-02-18
**Status**: Accepted

## Context

Amino is a schema-first classification rules engine. Before a significant rewrite, we needed to establish the core architectural decisions around data lifecycle, schema immutability, type enforcement, and multi-context use cases.

## Decisions

### 1. Three distinct data groups with different lifecycles

We model the system around three data groups:

- **Schema**: defines the type system (fields, types, structs, functions). Fixed.
- **Rules**: conditional logic compiled against the schema. Dynamic.
- **Decisions**: data items evaluated against compiled rules. Always dynamic.

These have fundamentally different lifecycles and must be treated as separate concerns in the implementation.

### 2. Schema is fixed at process start

The schema is the stable anchor for a running engine instance. It defines the structural contract between the data producer (the application) and the rules system.

**Rationale**: Schema changes are structural changes to the data model. A breaking change (field removed, type changed) invalidates all compiled rules that reference that field — meaning schema and rules cannot be independently hot-swapped in the general case. Treating schema as fixed eliminates a class of correctness bugs.

**Consequence**: Changing the schema requires replacing the engine (see Decision 4).

### 3. Rules are hot-swappable

Rules can be replaced while the engine is running without restarting the process. Two supported patterns:

- Rules loaded at startup alongside the schema (primary use case)
- Rules periodically replaced at runtime (e.g., policy updates, seasonal logic)
- Rules and decisions passed together for immediate one-shot evaluation

When rules are replaced, they are recompiled against the current (fixed) schema.

### 4. Zero-downtime reloads via atomic engine replacement

The primary zero-downtime mechanism is **atomic engine replacement**: the caller spins up a new engine instance with a new schema+rules, drains in-flight decisions against the old instance, then discards it.

Amino is responsible for making a single engine well-encapsulated and safely replaceable. The application is responsible for managing the swap (when to swap, draining in-flight work, discarding the old instance).

This pattern also handles schema changes: since the schema is fixed per engine instance, replacing the schema means replacing the engine.

### 5. Multi-context is an application-level concern

A "decision context" is a (schema, rules, validation modes) tuple. Running multiple contexts simultaneously — for example, different tenants with different schemas and rules — is handled by the application instantiating multiple engine instances and routing decisions accordingly.

Amino does not manage context naming, lifecycle, or routing. These are orchestration concerns outside the package boundary.

**Rationale**: Building multi-context management into amino would require context naming, routing, and lifecycle APIs that have nothing to do with rules evaluation. Applications are better positioned to own this logic.

### 6. Separate type enforcement modes for rules and decisions

Type enforcement is configurable independently for rules and decisions:

- **Rules mode** (`strict` | `loose`): controls how the engine responds when a rule fails type validation against the schema at compile time. In strict mode, bad rules raise an error. In loose mode, warnings are logged and the rule may be attempted.
- **Decisions mode** (`strict` | `loose`): controls how the engine responds when a decision (input data) fails type validation against the schema at evaluation time. In strict mode, non-conforming decisions are rejected with an error. In loose mode, non-conforming fields are skipped and a warning is logged; evaluation proceeds on the conforming fields only.

**Rationale**: Rules and decisions have different failure characteristics. A rule with a type mismatch (e.g., comparing a `Str` field to an `Int` literal) will never produce a correct result — strict is likely the right default. Decision data, particularly in IoT or high-volume pipelines, may be noisy or incomplete — loose may be the right default for those consumers.

**Loose mode semantics for decisions**: skip-and-warn. Non-conforming fields (wrong type or missing required field) are excluded from evaluation and a warning is emitted. The decision is evaluated on whatever conforming fields remain. Type coercion (e.g., `"600"` → `600`) is explicitly not performed — types are never silently changed.

## Consequences

- The engine is a single, well-encapsulated object representing one decision context.
- Schema immutability simplifies the type system: types are resolved at rule compile time against a stable schema.
- Rule hot-swap is supported natively; schema hot-swap is achieved by replacing the engine.
- Multi-context scenarios require no library support — just multiple engine instances.
- Type enforcement mode is a first-class concept, not an afterthought.

## Open Questions

None.
