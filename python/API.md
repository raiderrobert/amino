# API Reference

Everything public is importable from `amino` except the SQL backends, which live under `amino.backends` so that importing `amino` never touches a database driver.

## `load_schema()`

```python
engine = amino.load_schema(
    source,                      # str: path to a .amn file, or schema text
    *,
    funcs=None,                  # dict[str, Callable]
    rules_mode="strict",         # accepted; currently no effect (see below)
    decisions_mode="loose",      # "strict" | "loose"
    operators="standard",        # "standard" | "minimal" | list[str]
) -> Engine
```

- `source`: if it names a readable file, the file is parsed; otherwise the string itself is. Raises `SchemaParseError` or `SchemaValidationError`.
- `funcs`: implementations for functions declared in the schema. Same as calling `add_function()` for each.
- `rules_mode`: designed to choose between raising and warning on type mismatches in expressions. No mismatch is currently detected for built-in operators, so this has no effect. See [expression-language.md](../docs/expression-language.md#type-checking).
- `decisions_mode`: `"strict"` raises `DecisionValidationError` on a non-conforming record. `"loose"` drops non-conforming fields, adds a warning to `MatchResult.warnings`, and evaluates on what remains. Python target only.
- `operators`: the operator preset. See [expression-language.md](../docs/expression-language.md#operator-presets).

## Registration

All registration must happen before the first `parse()`, `compile()`, or `eval()`. After that the engine is frozen and any of these raises `EngineAlreadyFrozenError`.

### `add_function()`

```python
engine.add_function(name: str, fn: Callable) -> None
```

Provides the implementation for a function declared in the schema. Runs on the Python target only. SQL targets emit the name and expect the database to define it.

### `register_type()`

```python
engine.register_type(name: str, base: str, validator: Callable[[object], bool]) -> None
```

Makes `name` usable as a field type in the schema. `base` is one of `"Str"`, `"Int"`, `"Float"`, `"Bool"` and is what targets use for parameter types and default operator behaviour. `validator` runs during decision validation on the Python target. Registering a name that already exists, including a built-in like `email`, overwrites it.

Built-in custom types: `ipv4`, `ipv6`, `cidr`, `email`, `uuid`, all with base `Str`.

### `register_operator()`

```python
engine.register_operator(
    *,
    symbol: str | None = None,       # "|", "~", "->"
    keyword: str | None = None,      # "precedes", "overlaps"
    kind: str = "infix",             # "infix" | "prefix"
    fn: Callable,
    binding_power: int,
    associativity: str = "left",     # "left" | "right"
    input_types: tuple[str, ...] = ("*", "*"),
    return_type: str = "Bool",
) -> None
```

Exactly one of `symbol` or `keyword`. `"postfix"` is accepted but not implemented; it parses as infix. A duplicate token with the same `input_types` raises `OperatorConflictError`; the same token with different `input_types` is an overload and is dispatched by operand type. Custom operators run on the Python target only; SQL targets raise `UnsupportedExpressionError`.

## Parsing

### `parse()`

```python
engine.parse(text: str) -> Expression
```

Parses and type-checks one expression. Freezes the engine. Raises `RuleParseError` on a syntax error or an unknown field. The returned `Expression` can be given to any target.

### `Expression`

```python
expr.ast           # RuleAST: .root (a node) and .return_type
expr.schema        # SchemaRegistry
expr.types         # TypeRegistry
expr.base_type(type_name: str) -> str   # "email" -> "Str"; primitives return themselves
```

Frozen dataclass. Node types are in `amino.rules.ast`: `Literal`, `Variable`, `UnaryOp`, `BinaryOp`, `FunctionCall`. Each carries `type_name`.

### `export_schema()`

```python
engine.export_schema() -> str
```

The schema in `.amn` text. A JSON form that includes operator signatures is planned for client-side validators.

## Python target

### `eval()`

```python
engine.eval(rules: list[dict], decision: dict, match: dict | None = None) -> MatchResult
```

Parse, compile, and evaluate in one call. Convenient for one-offs. For repeated evaluation use `compile()`.

### `compile()`

```python
engine.compile(rules: list[dict], match: dict | None = None) -> CompiledRules
```

Rule dict format:

```python
{"id": ..., "rule": "credit_score < 600", "ordering": 1, ...}
```

`id` is required and must be unique within the set. `rule` is the expression text. `ordering` is used by `first` mode. Any other keys are kept as metadata.

### `CompiledRules`

```python
compiled.eval(decisions: list[dict]) -> list[MatchResult]
compiled.eval_single(decision: dict) -> MatchResult
```

Immutable. To change rules, compile again and swap the reference.

### Match config

```python
{"mode": "all"}                                                  # default
{"mode": "first", "key": "ordering", "order": "asc"}
{"mode": "inverse"}
{"mode": "score", "aggregate": "sum", "threshold": 0.7}
```

See [targets.md](../docs/targets.md#match-modes).

### `MatchResult`

```python
result.id         # the decision's "id" key, or None
result.matched    # list of rule ids (all, first, and score-with-threshold modes)
result.excluded   # list of rule ids that did not match (inverse mode)
result.score      # aggregate (score mode), else None
result.warnings   # list[str] from loose decisions mode
```

## SQL targets

```python
from amino.backends import Query, SQLBackend, ParamSink, UnsupportedExpressionError
from amino.backends.postgres import PostgresBackend
from amino.backends.clickhouse import ClickHouseBackend
```

### `PostgresBackend`, `ClickHouseBackend`

```python
backend = PostgresBackend(columns: dict[str, str] | None = None)
backend.compile(expr: Expression) -> Query
```

`columns` maps a field path to a SQL fragment rendered verbatim. Required for nested struct fields. Raises `UnsupportedExpressionError` for anything the backend cannot render.

### `Query`

```python
q.sql      # str, a predicate suitable for a WHERE clause
q.params   # list for Postgres, dict for ClickHouse
```

Frozen dataclass.

### `SQLBackend`

Abstract base. Subclass and implement `quote_ident()`, `new_params()`, `render_in()`, `render_contains()`. Optionally override `render_not_in()`. See [targets.md](../docs/targets.md#writing-a-target).

## Errors

All subclass `AminoError`, which carries `message`, `field`, `expected`, `got`.

| Error | Raised when |
|---|---|
| `SchemaParseError` | `.amn` text has a syntax error |
| `SchemaValidationError` | unknown type reference, circular struct, duplicate name, bad custom type base |
| `RuleParseError` | expression has a syntax error or references an unknown field |
| `TypeMismatchError` | reserved; not currently raised |
| `DecisionValidationError` | record fails validation in strict decisions mode |
| `RuleEvaluationError` | runtime failure inside the Python target; usually caught and turned into a false rule |
| `UnsupportedExpressionError` | a target cannot render part of an expression |
| `OperatorConflictError` | duplicate operator registration |
| `EngineAlreadyFrozenError` | registration after first use |
