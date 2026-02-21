# Rule Expression Language Reference

## Overview

A rule expression is a string evaluated against a decision dict. Rules are compiled against the schema at engine construction time (or when `compile()` or `eval()` is called) and evaluated against incoming decision data at runtime. The result of a rule expression is typically `Bool`, but `Int` and `Float` results are valid for scoring rules.

## Atoms

Atoms are the leaf elements of an expression.

**Identifiers and dot-notation variable references** — field references that resolve against the schema. Dot notation traverses struct fields:

```
age
customer.billing_address.city
order.items
```

**Literals** — string, int, float, bool, and list literals:

```
'San Francisco'     # string (single-quoted)
600                 # integer
600.0               # float (tried before integer in the parser)
true                # boolean
false               # boolean
['a', 'b', 'c']    # list literal
```

**Function calls** — `identifier` immediately followed by `(`:

```
validate_address(customer.billing_address)
score_customer(id, tier)
```

**Parenthesized expressions** — explicit grouping:

```
(age >= 18 and age <= 65)
```

## Operator system

The rule expression language uses a Pratt (top-down operator precedence) parser with a dynamic operator table. Operators have:

- **Binding power** — integer determining precedence relative to all other operators
- **Associativity** — `'left'` or `'right'`
- **Type signatures** — `input_types` and `return_type` for compile-time type checking

The operator table is initialized at engine construction from the selected preset and any custom operator registrations. The Pratt parser's `nud`/`led` dispatch handles operator parsing dynamically, so operator precedence and type checking extend naturally to custom operators.

## Operator presets

The preset is selected at engine construction via the `operators` parameter of `load_schema()`.

| Preset | Operators included |
|--------|-------------------|
| `'standard'` (default) | `and`, `or`, `not`, `=`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`, `contains` |
| `'minimal'` | `and`, `or`, `not` only |
| `list[str]` | Explicit list of named built-in operators |

`and`, `or`, `not`, and parentheses are the irreducible minimum and are always present regardless of preset — even `'minimal'` includes them. This allows compound rules (`A precedes B and C precedes D`) to work in domains that use a fully custom operator vocabulary.

## Built-in binding powers

```
or           →  10
and          →  20
not          →  30  (prefix)
in, not in   →  40
=, !=        →  40
>, <, >=, <= →  40
```

Use these values as reference points when choosing binding powers for custom operators.

## Keyword operator disambiguation

`identifier '('` is always a function call. `identifier` in infix position (between two expressions, not followed by `(`) is a keyword operator dispatched through the Pratt `led` table.

A keyword operator `precedes` and a function `precedes(a, b)` can coexist in the same engine without conflict. The tokenizer does not resolve this — the Pratt parser's nud/led dispatch handles it based on position in the expression.

## Custom operators

Custom operators are registered via `engine.register_operator()` before the first `compile()` or `eval()` call.

```python
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

Exactly one of `symbol` or `keyword` must be provided. `input_types` and `return_type` are required — they enable compile-time type checking in the TypedCompiler.

**Symbolic operator example:**

```python
engine.register_operator(
    symbol='|',
    fn=ip_union,
    binding_power=40,
    associativity='left',
    input_types=('cidr', 'cidr'),
    return_type='cidr',
)
```

**Keyword operator example:**

```python
engine.register_operator(
    keyword='precedes',
    fn=event_precedes,
    binding_power=40,
    input_types=('Str', 'Str'),
    return_type='Bool',
)
```

Registering a duplicate symbol or keyword raises `OperatorConflictError`. Registering after the engine is frozen raises `EngineAlreadyFrozenError`.

## Match modes

The match mode determines how rule results are aggregated into a `MatchResult`. It is specified in the `match` dict passed to `compile()` or `eval()`.

| Mode | Description | Key `MatchResult` fields |
|------|-------------|--------------------------|
| `'all'` (default) | All rules that match | `matched: list[str]` |
| `'first'` | First match by ordering | `matched: list[str]` (length 0 or 1) |
| `'inverse'` | All rules that do NOT match | `excluded: list[str]` |
| `'score'` | Aggregate rule scores | `score: float` |

**Score mode Bool coercion:** `Bool` results coerce numerically — `True` → `1`, `False` → `0`. This allows boolean and numeric rules to coexist in a scored rule set without special cases. `aggregate` defaults to `'sum'`.

## Match config format

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

## Grammar

See [docs/grammar/rules.peg](grammar/rules.peg) for the formal grammar of the irreducible minimum.
