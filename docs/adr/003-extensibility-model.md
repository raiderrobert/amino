# ADR 003: Extensibility Model

**Date**: 2026-02-19
**Status**: Accepted

## Context

Amino is designed for use cases that go beyond a fixed rule grammar operating on a fixed set of types and returning a boolean result. Different problem domains require different operator vocabularies, different data types with domain-specific validation, and different result semantics. The extensibility model must support these cases without requiring changes to the core library.

Three extension points were identified: the operator system, the type system, and the result/match system.

## Decisions

### 1. Rule expression grammar is configurable via operator presets

The rule expression language is not a single fixed grammar. It is a configurable grammar instantiated per engine. Operators are registered into a Pratt parser (top-down operator precedence), which gives each operator a numeric binding power determining its precedence relative to all other operators.

Two built-in presets are provided:

- `'standard'` (default) — all built-in operators: `and`, `or`, `not`, `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`
- `'minimal'` — no comparison or membership operators; only the irreducible minimum (see Decision 3)

Users can also pass an explicit list of built-in operator names to enable a specific subset.

```python
# Standard use case — full built-in operator set (default)
engine = amino.load_schema("schema.amn")

# DAG validation — minimal base, custom operators added
engine = amino.load_schema("schema.amn", operators='minimal')
engine.register_operator(keyword='precedes', fn=dag_precedes, binding_power=40)
engine.register_operator(symbol='->', fn=dag_edge, binding_power=40)

# Selective subset of built-ins plus a custom operator
engine = amino.load_schema("schema.amn", operators=['and', 'or', 'not', '=', '!='])
engine.register_operator(symbol='|', fn=ip_union, binding_power=40,
                         input_types=('cidr', 'cidr'), return_type='cidr')
```

**Rationale**: Different problem domains have fundamentally different operator vocabularies. Preset-based configuration with a sensible default is ergonomic for the common case and powerful for custom cases. The DAG validation use case can start from `'minimal'` and register only what it needs, while still having `and`/`or`/`not` available for compound rules like `A precedes B and C precedes D`.

### 2. Custom operators are registered with explicit binding power, associativity, and type signature

When registering a custom operator, the caller specifies:

- `symbol` (for symbolic infix operators: `|`, `^`, `->`) or `keyword` (for word operators: `precedes`, `overlaps`, `contains`)
- `kind`: `'infix'` (default), `'prefix'`, or `'postfix'`
- `fn`: the callable implementing the operation
- `binding_power`: integer determining precedence
- `associativity`: `'left'` (default) or `'right'`
- `input_types`: tuple of expected operand type names (e.g., `('cidr', 'cidr')`)
- `return_type`: the type name the operator produces (e.g., `'cidr'`, `'Bool'`)

```python
# Infix symbolic operator
engine.register_operator(
    symbol='|',
    fn=ip_union,
    binding_power=40,
    associativity='left',
    input_types=('cidr', 'cidr'),
    return_type='cidr',
)

# Infix keyword operator
engine.register_operator(
    keyword='precedes',
    fn=event_precedes,
    binding_power=40,
    input_types=('Str', 'Str'),
    return_type='Bool',
)

# Prefix operator
engine.register_operator(
    symbol='~',
    kind='prefix',
    fn=bitwise_not,
    binding_power=50,
    input_types=('Int',),
    return_type='Int',
)
```

Built-in binding powers (for reference when choosing custom values):
```
or           →  10
and          →  20
not          →  30  (prefix)
in, not in   →  40
=, !=        →  40
>, <, >=, <= →  40
```

`input_types` and `return_type` are required. They allow the TypedCompiler to type-check expressions containing custom operators at compile time and to determine the return type of enclosing expressions.

**Conflict policy**: Registering an operator with a symbol or keyword that is already registered raises an error. Operators must be registered before the first `compile()` or `eval()` call; registration after first use raises an error.

**Rationale**: A Pratt parser naturally supports dynamic operator tables via binding power. Requiring explicit type signatures enables compile-time type checking for all expressions, including those involving custom operators.

### 3. The irreducible minimum grammar is always present

Regardless of operator configuration (including `'minimal'`), the following are always available in rule expressions and cannot be de-registered:

- Identifiers and dot-notation field references (`customer.tier`)
- String, number, and boolean literals
- Parentheses for explicit grouping
- Function call syntax (`fn(arg1, arg2)`)
- Logical connectives: `and`, `or`, `not`

Logical connectives are part of the irreducible minimum because compound rules (`A precedes B and C precedes D`) are useful in almost every domain, including those that want a custom operator vocabulary. The `'minimal'` preset excludes all comparison and membership operators, but preserves logical connectives.

### 4. Keyword operators and function calls are disambiguated by syntax

Keyword operators and function calls occupy the same identifier namespace but are distinguished syntactically:

- `fn(arg1, arg2)` — function call: identifier immediately followed by `(`
- `A keyword B` — keyword operator: identifier in infix position, not followed by `(`

A keyword operator `precedes` and a function `precedes(a, b)` can coexist in the same engine without conflict. The tokenizer does not resolve this — the Pratt parser's nud/led dispatch handles it based on position in the expression.

### 5. Custom types are registered with validators and a base type

The type system is extensible. Users register custom types by providing:
- A type name (used in schema definitions)
- A base type (`Str`, `Int`, `Float`, or `Bool`) for storage and default operator behavior
- A validator function that receives a value and returns a validation result

```python
engine.register_type('ipv4', base='Str', validator=is_valid_ipv4)
engine.register_type('ipv6', base='Str', validator=is_valid_ipv6)
engine.register_type('cidr', base='Str', validator=is_valid_cidr)
```

Once registered, the type name is valid in schema definitions:
```
source_ip: ipv4
network:   cidr
```

Custom types participate in the type system: the TypedCompiler uses their base type for compatibility checking when no type-specific operator is registered, and the DecisionValidator runs their validator against incoming decision data.

**Rationale**: Domain-specific types cannot all be anticipated. The base type determines what built-in operators work by default. Type-specific operators (registered with matching `input_types`) override built-in operator behavior for that type combination, allowing IP-aware comparison or decimal-safe arithmetic without special casing in the core.

Type registrations, like operator registrations, must occur before the first `compile()` or `eval()` call.

### 6. Rules can return non-boolean results

Rules are not required to resolve to boolean values. The result type is determined by the expression and annotated by the TypedCompiler:

- `Bool` — standard true/false match (most common)
- `Int` or `Float` — scoring rules that return a numeric value

### 7. Match modes

The matcher supports configurable result modes, specified at `compile()` time:

- `'all'` — return all matching rules per decision (default)
- `'first'` — return the first matching rule by ordering
- `'inverse'` — return all rules that do NOT match (useful for eligibility/disqualification)
- `'score'` — aggregate numeric scores across all rules per decision, with optional threshold

```python
compiled = engine.compile(rules, match={'mode': 'first', 'key': 'ordering', 'order': 'asc'})
compiled = engine.compile(rules, match={'mode': 'score', 'threshold': 0.7, 'aggregate': 'sum'})
compiled = engine.compile(rules, match={'mode': 'inverse'})
```

**Score mode boolean coercion**: In `'score'` mode, `Bool` rule results coerce numerically — `True` → `1`, `False` → `0`. This follows Python semantics and allows boolean and numeric rules to coexist in a scored rule set without special cases.

**Rationale**: Real-world decision systems require more than boolean pass/fail. Fraud detection needs score aggregation. Eligibility engines need "all disqualifying rules." Content moderation needs "first applicable policy."

## Consequences

- The rule expression parser (Pratt parser) is dynamic: initialized with the operator set at engine construction time. This requires a full Pratt parser implementation — the existing recursive descent parser with hardcoded precedence must be replaced.
- A separate `operators/` module houses the operator registry and preset definitions.
- The `types/` module is a first-class extension point, not an optional add-on.
- The matcher supports four modes: `all`, `first`, `inverse`, `score`.
- Custom operators carry type signatures, enabling compile-time type checking throughout.
- All registrations (operators, types, functions) must be completed before first use. The engine enforces this invariant.
- The schema language grammar remains fully static PEG — only the rule expression grammar is configurable via the Pratt operator table.

## Open Questions

- Should built-in operator names (e.g., `'and'`, `'or'`) be exported as constants to avoid stringly-typed preset lists?
- Score aggregation modes beyond `sum` (e.g., `max`, `weighted_sum`) — deferred to implementation.
