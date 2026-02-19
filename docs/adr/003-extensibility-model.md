# ADR 003: Extensibility Model

**Date**: 2026-02-18
**Status**: Accepted

## Context

Amino is designed for use cases that go beyond a fixed rule grammar operating on a fixed set of types and returning a boolean result. Different problem domains require different operator vocabularies, different data types with domain-specific validation, and different result semantics. The extensibility model must support these cases without requiring changes to the core library.

Three extension points were identified: the operator system, the type system, and the result/match system.

## Decisions

### 1. Rule expression grammar is configurable via operator presets

The rule expression language is not a single fixed grammar. It is a configurable grammar instantiated per engine. Operators are registered into a Pratt parser (top-down operator precedence), which gives each operator a numeric binding power determining its precedence relative to all other operators.

The `'standard'` preset is the default and includes all built-in operators. Users can override this with a different preset or an explicit list of operator names.

```python
# Standard use case — full built-in operator set (default)
engine = amino.load_schema("schema.amn")
engine = amino.load_schema("schema.amn", operators='standard')

# DAG validation — clean slate
engine = amino.load_schema("schema.amn", operators='none')
engine.register_operator(keyword='precedes', fn=dag_precedes, binding_power=40)
engine.register_operator(symbol='->', fn=dag_edge, binding_power=40)

# Selective subset
engine = amino.load_schema("schema.amn", operators=['and', 'or', 'not', '=', '!='])
engine.register_operator(symbol='|', fn=ip_union, binding_power=40)
```

**Rationale**: Different problem domains have fundamentally different operator vocabularies. A DAG validation engine where rules look like `A precedes B` should not be burdened with or confused by `and`, `or`, `=`, and `!=`. Preset-based configuration with a sensible default is ergonomic for the common case and powerful for custom cases.

### 2. Custom operators are registered with explicit binding power

When registering a custom operator, the caller specifies:
- `symbol` (for symbolic infix operators: `|`, `^`, `->`) or `keyword` (for word operators: `precedes`, `overlaps`, `contains`)
- `fn`: the callable that implements the operation, called as `fn(left, right)` for infix operators
- `binding_power`: integer determining precedence relative to built-in operators

Built-in binding powers (for reference when choosing custom values):
```
or           →  10
and          →  20
not          →  30  (prefix)
in, not in   →  40
=, !=        →  40
>, <, >=, <= →  40
```

Operators can be registered and de-registered at engine construction time. Operators are fixed for the lifetime of an engine instance, consistent with the schema-fixed-at-startup principle.

**Rationale**: A Pratt parser naturally supports dynamic operator tables via binding power. Numeric binding power gives callers precise control over associativity and precedence without requiring knowledge of grammar internals. The schema language and rule expression language are separate parsers, so symbols like `->` can mean one thing in schema declarations and another in rule expressions without conflict.

### 3. The irreducible minimum grammar is always present

Regardless of operator configuration, the following are always available in rule expressions:
- Identifiers and dot-notation field references (`customer.tier`)
- String, number, and boolean literals
- Parentheses for explicit grouping
- Function call syntax (`fn(arg1, arg2)`)

These cannot be de-registered. Everything else — including `and`, `or`, `not`, `=`, etc. — is part of the operator system and subject to the preset configuration.

### 4. Custom types are registered with validators and a base type

The type system is extensible. Users register custom types by providing:
- A type name (used in schema definitions)
- A base type (`Str`, `Int`, `Float`, or `Bool`) for storage and default behavior
- A validator function that receives a value and returns a validation result

```python
engine.register_type('ipv4',  base='Str', validator=is_valid_ipv4)
engine.register_type('ipv6',  base='Str', validator=is_valid_ipv6)
engine.register_type('cidr',  base='Str', validator=is_valid_cidr)
```

Once registered, the type name is valid in schema definitions:
```
source_ip: ipv4
network:   cidr
```

Custom types participate in the type system: the TypedCompiler knows their base type for compatibility checking, and the DecisionValidator runs their validator against incoming decision data.

**Rationale**: Domain-specific types (IP addresses, CIDR notation, monetary amounts, ISO codes) cannot all be anticipated. A registration mechanism lets users bring their own types without forking the library.

### 5. Rules can return non-boolean results

Rules are not required to resolve to boolean values. The result type of a rule is determined by the expression it evaluates. The compiler annotates the rule AST with its return type, which can be:
- `Bool` — standard true/false match (most common)
- `Int` or `Float` — scoring rules that return a numeric value

**Rationale**: Scoring use cases (e.g., fraud risk scores, relevance ranking) require numeric rule results. A rule like `toxicity_score(content.text)` returns a Float and should be usable directly as a rule result.

### 6. Match modes are extensible

The matcher supports configurable result modes, specified at `compile()` time:

- `all` — return all matching rules (default)
- `first` — return the first matching rule by ordering
- `none` — return all rules that do NOT match (inverse)
- `score` — aggregate numeric scores across matching rules, with optional threshold

```python
compiled = engine.compile(rules, match={'mode': 'first', 'key': 'ordering', 'order': 'asc'})
compiled = engine.compile(rules, match={'mode': 'score', 'threshold': 0.7, 'aggregate': 'sum'})
compiled = engine.compile(rules, match={'mode': 'none'})
```

**Rationale**: Real-world decision systems require more than boolean pass/fail. Fraud detection needs score aggregation. Eligibility engines need "all disqualifying rules." Content moderation needs "first applicable policy."

## Consequences

- The rule expression parser (Pratt parser) is dynamic: initialized with the operator set at engine construction time.
- A separate `operators/` module houses the operator registry and standard preset.
- The `types/` module returns to the codebase as a proper first-class extension point.
- The matcher gains additional modes beyond `ALL` and `FIRST`.
- The schema language grammar remains fully static PEG — only the rule expression grammar is configurable.
- Engine construction is now more involved: schema + operator preset + type registrations + function registrations.

## Open Questions

- What is the API for operator de-registration after engine construction, if any? Current decision: operators are fixed at construction time, consistent with schema immutability.
- Should built-in operator names (e.g., `'and'`, `'or'`) be exported as constants to avoid stringly-typed preset lists?
- Score aggregation modes beyond `sum` (e.g., `max`, `weighted_sum`) — deferred to implementation.
