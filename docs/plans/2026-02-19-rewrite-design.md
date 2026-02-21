# Amino Rewrite Design

**Date**: 2026-02-19
**Status**: Approved
**ADRs**: 001, 002, 003, 004

## Overview

Amino is a schema-first classification rules engine. The schema defines the type system; rules are compiled against it; decisions (input data) are evaluated against compiled rules. The rewrite establishes a correct type system, an extensible operator model, and a clean engine lifecycle.

---

## Architecture

### Pipeline

```
Schema text  ──▶  Schema Parser  ──▶  SchemaAST  ──▶  Schema Validator
                  (static PEG)                         (refs, circularity,
                                                        duplicate names)
                                                             │
                                                             ▼
                                                       SchemaRegistry
                                                       (fast lookup,
                                                        export)
                                                             │
                  ┌──────────────────────────────────────────┤
                  │ fixed for engine lifetime                 │
                  ▼                                           │
           OperatorRegistry  ◀── register_operator()         │
           TypeRegistry      ◀── register_type()             │
           FunctionRegistry  ◀── add_function()              │
                  │ (all frozen after first compile/eval)     │
                  ▼                                           │
Rule text  ──▶  Rule Parser  ──▶  RuleAST  ──▶  TypedCompiler  ──▶  CompiledRule
               (Pratt parser,                    (type resolution
                dynamic op table)                + optimization
                                                 + codegen,
                                                 one AST walk)

Decision dict  ──▶  DecisionValidator  ──▶  Evaluator  ──▶  Matcher  ──▶  MatchResult
                     (schema + constraints,    (runs              (all / first /
                      strict / loose mode)     CompiledRules)      inverse / score)
```

### File Structure

```
amino/
├── __init__.py              # Public API: load_schema()
├── engine.py                # Engine class: orchestrates registries, enforces freeze-before-use
├── schema/
│   ├── __init__.py
│   ├── parser.py            # PEG parser for .amn schema files (static grammar)
│   ├── ast.py               # Schema AST nodes + SchemaType enum
│   └── registry.py          # SchemaRegistry: field/struct lookup + schema export
│   └── validator.py         # Schema self-consistency: refs, circular structs, duplicates
├── rules/
│   ├── __init__.py
│   ├── parser.py            # Pratt parser for rule expressions (dynamic operator table)
│   ├── ast.py               # Rule AST nodes, annotated with resolved types + return type
│   └── compiler.py          # TypedCompiler: type resolution + optimization + codegen
├── operators/
│   ├── __init__.py
│   ├── registry.py          # OperatorRegistry: symbol/keyword → OperatorDef
│   └── standard.py          # 'standard' and 'minimal' preset definitions
├── types/
│   ├── __init__.py
│   ├── registry.py          # TypeRegistry: name → TypeDef (base type + validator)
│   └── builtin.py           # Pre-defined types: ipv4, ipv6, cidr, email, uuid, etc.
├── runtime/
│   ├── __init__.py
│   ├── compiled_rules.py    # CompiledRules: returned by compile(), owns match config
│   ├── validator.py         # DecisionValidator: validates decisions against schema + constraints
│   ├── evaluator.py         # Executes compiled rules against a validated decision
│   └── matcher.py           # Applies match mode to rule results → MatchResult
└── errors.py                # Exception hierarchy
```

---

## Public API

### Engine construction

```python
engine = amino.load_schema(
    source,                      # str — file path or raw schema text
    *,
    funcs=None,                  # dict[str, Callable] | None
    rules_mode='strict',         # 'strict' | 'loose'
    decisions_mode='loose',      # 'strict' | 'loose'
    operators='standard',        # 'standard' | 'minimal' | list[str]
) -> Engine
```

### Registration (must complete before first compile/eval)

```python
engine.add_function(name: str, fn: Callable) -> None

engine.register_type(
    name: str,
    base: str,           # 'Str' | 'Int' | 'Float' | 'Bool'
    validator: Callable, # fn(value) -> bool | ValidationResult
) -> None

engine.register_operator(
    *,
    symbol: str = None,          # symbolic: '|', '^', '->'
    keyword: str = None,         # word: 'precedes', 'overlaps'
    kind: str = 'infix',         # 'infix' | 'prefix' | 'postfix'
    fn: Callable,
    binding_power: int,
    associativity: str = 'left', # 'left' | 'right'
    input_types: tuple[str, ...],
    return_type: str,
) -> None
```

Exactly one of `symbol` or `keyword` must be provided. Registering a duplicate symbol/keyword raises `OperatorConflictError`. Calling any registration method after the first `compile()` or `eval()` raises `EngineAlreadyFrozenError`.

### Evaluation

```python
# One-shot: parse + compile + evaluate in one call
engine.eval(
    rules: list[dict],   # same format as compile()
    decision: dict,
    match: dict = None,
) -> MatchResult

# Compile a rule set for repeated evaluation
engine.compile(
    rules: list[dict],   # [{'id': str, 'rule': str, 'ordering': int, ...}]
    match: dict = None,
) -> CompiledRules

# Hot-swap rules atomically
engine.update_rules(rules: list[dict]) -> None

# Schema introspection
engine.export_schema() -> str   # returns schema in .amn format
```

### Rule dict format

```python
{
    'id': str,           # required, unique within the rule set
    'rule': str,         # required, rule expression string
    'ordering': int,     # optional, used by 'first' match mode
    # any additional keys are stored as metadata on the rule
}
```

### Match config format

```python
# Return all matching rules (default)
match = None
match = {'mode': 'all'}

# Return first match by ordering
match = {'mode': 'first', 'key': 'ordering', 'order': 'asc'}

# Return all non-matching rules
match = {'mode': 'inverse'}

# Aggregate scores, optional threshold
match = {'mode': 'score', 'aggregate': 'sum', 'threshold': 0.7}
```

### CompiledRules

```python
compiled.eval(decisions: list[dict]) -> list[MatchResult]
compiled.eval_single(decision: dict) -> MatchResult
```

### MatchResult

```python
result.id        # str | None — decision identifier (from 'id' key in decision dict)
result.matched   # list[str] — matched rule ids ('all' and 'first' modes)
result.excluded  # list[str] — non-matching rule ids ('inverse' mode)
result.score     # float | None — aggregated score ('score' mode)
result.warnings  # list[str] — validation warnings (loose mode only)
```

---

## Schema Language Grammar (PEG)

See [`docs/grammar/schema.peg`](../grammar/schema.peg) for the full PEG grammar.

---

## Rule Expression Grammar (Pratt Parser)

See [`docs/grammar/rules.peg`](../grammar/rules.peg) for the rule expression grammar.

---

## Type System

### Primitive types

| Name    | Python equivalent | Notes |
|---------|------------------|-------|
| `Int`   | `int`            |       |
| `Float` | `float`          |       |
| `Str`   | `str`            |       |
| `Bool`  | `bool`           |       |

### Complex types

- `List[T]` — homogeneous or union-typed list: `List[Float]`, `List[Int|Str|Bool]`
- Struct — named group of fields, referenced by name as a type

### Custom types

Registered via `engine.register_type(name, base, validator)`. Custom types have a base primitive type that governs default operator behavior. The validator runs during decision validation.

### Constraints (schema-level)

Declared inline on field definitions. Enforced by `DecisionValidator` at evaluation time, not by the compiler.

| Constraint | Applicable types | Meaning |
|-----------|-----------------|---------|
| `min` / `max` | Int, Float | Inclusive numeric bounds |
| `exclusiveMin` / `exclusiveMax` | Int, Float | Exclusive numeric bounds |
| `minLength` / `maxLength` / `exactLength` | Str | Character count bounds |
| `pattern` | Str | Regex pattern the value must match |
| `format` | Str | Named format validator (email, url, uuid, etc.) |
| `oneOf` | Any | Value must be one of the listed literals |
| `const` | Any | Value must equal exactly this literal |
| `minItems` / `maxItems` / `exactItems` | List | Element count bounds |
| `unique` | List | All elements must be distinct |

### Type enforcement modes

Configured at engine construction via `rules_mode` and `decisions_mode`:

- `strict` rules mode: type mismatch in a rule expression raises `TypeMismatchError` at `compile()` time
- `loose` rules mode: type mismatch logs a warning; the rule is compiled with best-effort type information
- `strict` decisions mode: non-conforming decision data raises `DecisionValidationError`
- `loose` decisions mode: non-conforming fields are skipped; a warning is added to `MatchResult.warnings`

---

## Operator System

### Built-in presets

| Preset | Operators included |
|--------|-------------------|
| `'standard'` (default) | `and`, `or`, `not`, `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in` |
| `'minimal'` | `and`, `or`, `not` only (all comparison/membership operators excluded) |
| `list[str]` | Explicit list of named built-in operators |

`and`, `or`, `not`, and parentheses are part of the irreducible minimum and are always available even with `operators='minimal'`.

### Custom operator registration

```python
engine.register_operator(
    symbol='|',             # XOR: symbol OR keyword, not both
    kind='infix',           # 'infix' (default) | 'prefix' | 'postfix'
    fn=ip_union,
    binding_power=40,
    associativity='left',   # 'left' (default) | 'right'
    input_types=('cidr', 'cidr'),
    return_type='cidr',
)
```

- `input_types` and `return_type` are required. They enable compile-time type checking in the TypedCompiler.
- Duplicate symbol/keyword: raises `OperatorConflictError`.
- Registration after first `compile()`/`eval()`: raises `EngineAlreadyFrozenError`.

---

## Engine Lifecycle

```
Construction  │  load_schema() parses schema, builds SchemaRegistry, sets modes and preset
              │
Registration  │  register_type(), register_operator(), add_function()
              │  All registrations must complete before first compile/eval
              │
  ┌── Freeze ─┘  First compile() or eval() freezes all registries
  │
  │  Hot-swap │  update_rules() atomically replaces compiled rules;
  │           │  schema and registries remain unchanged
  │
  └── Replace │  For schema changes: caller spins up a new Engine,
              │  drains in-flight decisions against old engine, discards it
```

---

## Error Hierarchy

```
AminoError
├── SchemaParseError           # Syntax error in .amn schema file
├── SchemaValidationError      # Semantic error: unknown type ref, circular struct, duplicate name
├── RuleParseError             # Syntax error in rule expression string
├── TypeMismatchError          # Type error caught at rule compile time
├── DecisionValidationError    # Decision data fails schema/constraint validation (strict mode)
├── RuleEvaluationError        # Runtime error during rule evaluation
├── OperatorConflictError      # Duplicate operator registration
└── EngineAlreadyFrozenError   # Registration attempted after first use
```

All errors carry a `message: str` and where applicable `field: str`, `expected: str`, `got: str` for structured error handling.

---

## Match Modes

| Mode | Description | Key `MatchResult` fields |
|------|-------------|--------------------------|
| `'all'` (default) | All rules that match | `matched: list[str]` |
| `'first'` | First match by ordering | `matched: list[str]` (length 0 or 1) |
| `'inverse'` | All rules that do NOT match | `excluded: list[str]` |
| `'score'` | Aggregate rule scores | `score: float` |

**Score mode:** `Bool` results coerce to `1` (True) or `0` (False). `Int`/`Float` results pass through. `aggregate` defaults to `'sum'`.

---

## What Changes from the Current Codebase

| Current | Rewrite |
|---------|---------|
| `amino/rules/optimizer.py` | Removed — optimization folded into TypedCompiler single-pass walk |
| `amino/types/` directory | Returns as first-class extension point (`types/registry.py`, `types/builtin.py`) |
| `amino/utils/` directory | Removed — `errors.py` at top level; reserved keyword list moves to `rules/parser.py` |
| `amino/core.py` | Replaced by `engine.py` |
| `Schema` class | Renamed to `Engine`; `load_schema()` returns `Engine` |
| Recursive descent rule parser | Replaced by Pratt parser with dynamic operator table |
| Type system decorative | Type resolution enforced in TypedCompiler; decisions validated against schema |
| `BEST` match mode | Removed (was an infinite recursion bug); replaced by `'inverse'` and `'score'` |
| `amino/runtime/compiled_rules.py` | Retained and expanded |
