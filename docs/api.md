# Public API Reference

## Engine construction

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

**Parameters:**

- `source` — a file path to a `.amn` schema file, or raw schema text as a string. The schema is parsed and validated immediately; `SchemaParseError` or `SchemaValidationError` is raised on failure.
- `funcs` — optional dict of `{name: callable}` pairs to register as functions at construction time. Equivalent to calling `engine.add_function()` for each entry.
- `rules_mode` — type enforcement mode for rule expressions. `'strict'` raises `TypeMismatchError` at compile time on type mismatches. `'loose'` logs a warning and compiles with best-effort type information. Default: `'strict'`.
- `decisions_mode` — type enforcement mode for decision data. `'strict'` raises `DecisionValidationError` on non-conforming decisions. `'loose'` skips non-conforming fields and adds a warning to `MatchResult.warnings`. Default: `'loose'`.
- `operators` — operator preset for the rule expression parser. `'standard'` includes all built-in operators. `'minimal'` includes only `and`, `or`, `not`. A `list[str]` selects a specific subset of built-in operator names. Default: `'standard'`.

## Registration

All registrations must complete before the first `compile()` or `eval()` call. After first use, the engine is frozen and any registration attempt raises `EngineAlreadyFrozenError`.

### `add_function()`

```python
engine.add_function(name: str, fn: Callable) -> None
```

Registers a callable as a named function available in rule expressions. The function can then be called as `name(args...)` in rule strings.

### `register_type()`

```python
engine.register_type(
    name: str,
    base: str,           # 'Str' | 'Int' | 'Float' | 'Bool'
    validator: Callable, # fn(value) -> bool | ValidationResult
) -> None
```

Registers a custom type. Once registered, `name` is valid in schema field definitions. The `base` type determines default operator behavior when no type-specific operator is registered. The `validator` runs during decision validation.

### `register_operator()`

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

Registers a custom operator. Exactly one of `symbol` or `keyword` must be provided. `input_types` and `return_type` are required for compile-time type checking. Registering a duplicate symbol or keyword raises `OperatorConflictError`.

## Evaluation

### `eval()`

```python
engine.eval(
    rules: list[dict],   # same format as compile()
    decision: dict,
    match: dict = None,
) -> MatchResult
```

One-shot evaluation: parses, compiles, and evaluates in a single call. Useful for ad-hoc or low-frequency evaluation. For repeated evaluation against the same rule set, prefer `compile()` + `CompiledRules.eval()`.

### `compile()`

```python
engine.compile(
    rules: list[dict],   # [{'id': str, 'rule': str, 'ordering': int, ...}]
    match: dict = None,
) -> CompiledRules
```

Compiles a rule set for repeated evaluation. Returns a `CompiledRules` object. Calling `compile()` freezes the engine's registries.

### `update_rules()`

```python
engine.update_rules(rules: list[dict]) -> None
```

Atomically hot-swaps the compiled rule set. Schema and registries remain unchanged. The new rules are compiled against the same (fixed) schema.

### `export_schema()`

```python
engine.export_schema() -> str
```

Returns the current schema in `.amn` format. Enables client SDKs to fetch the schema for local preflight validation.

## Rule dict format

```python
{
    'id': str,           # required, unique within the rule set
    'rule': str,         # required, rule expression string
    'ordering': int,     # optional, used by 'first' match mode
    # any additional keys are stored as metadata on the rule
}
```

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

## CompiledRules

`CompiledRules` is returned by `engine.compile()`. It holds the compiled rule set and match configuration, and can be evaluated against multiple decisions without recompilation.

```python
compiled.eval(decisions: list[dict]) -> list[MatchResult]
compiled.eval_single(decision: dict) -> MatchResult
```

## MatchResult

```python
result.id        # str | None — decision identifier (from 'id' key in decision dict)
result.matched   # list[str] — matched rule ids ('all' and 'first' modes)
result.excluded  # list[str] — non-matching rule ids ('inverse' mode)
result.score     # float | None — aggregated score ('score' mode)
result.warnings  # list[str] — validation warnings (loose mode only)
```

- `id` — taken from the `'id'` key in the decision dict, if present.
- `matched` — populated by `'all'` and `'first'` modes. Empty list if no rules match.
- `excluded` — populated by `'inverse'` mode. Contains rule ids that did not match.
- `score` — populated by `'score'` mode. `None` in all other modes.
- `warnings` — populated when `decisions_mode='loose'` and non-conforming fields are encountered. Empty list in strict mode.
