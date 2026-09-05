# Targets

A target consumes a parsed, type-checked expression and turns it into something that runs. The parser and type checker are shared; a target is only the part that differs.

```python
import amino

engine = amino.load_schema("schema.amn")
expr = engine.parse("score > 40 and name contains 'ob'")   # one Expression
```

`engine.parse()` freezes the engine, since operator resolution happens during parsing. Register custom types, operators, and functions first.

Three targets ship with amino. The first is the original rules engine.

## Python evaluator

Evaluates one or many expressions against one or many records, in process. The API calls expressions "rules" and records "decisions" because that is the vocabulary of its main use.

### One-shot

```python
result = engine.eval(
    rules=[{"id": "decline", "rule": "credit_score < 600 or income < 30000"}],
    decision={"credit_score": 580, "income": 45000, "amount": 75000, "state_code": "CA"},
)
result.matched   # ['decline']
```

### Compile once, evaluate many

```python
compiled = engine.compile(
    rules=[
        {"id": "high_risk",   "rule": "credit_score < 500",                   "ordering": 1},
        {"id": "ca_income",   "rule": "state_code = 'CA' and income < 50000",  "ordering": 2},
        {"id": "amount_risk", "rule": "credit_score < 650 and amount > 40000", "ordering": 3},
    ],
    match={"mode": "first", "key": "ordering", "order": "asc"},
)

for result in compiled.eval(decisions):
    result.id, result.matched
```

`CompiledRules` is immutable. To change the rule set, call `compile()` again and swap the reference. The schema and registries are unchanged, so this is cheap and atomic from the caller's point of view.

### Match modes

Passed as the `match` argument to `compile()` or `eval()`.

| Mode | Returns | Config |
|---|---|---|
| `all` (default) | every rule that matched, in `result.matched` | `{'mode': 'all'}` |
| `first` | the single earliest match by a key, in `result.matched` | `{'mode': 'first', 'key': 'ordering', 'order': 'asc'}` |
| `inverse` | every rule that did not match, in `result.excluded` | `{'mode': 'inverse'}` |
| `score` | the aggregate of rule results, in `result.score` | `{'mode': 'score', 'aggregate': 'sum', 'threshold': 0.7}` |

In `score` mode, `Bool` results coerce to `1` and `0`, so boolean and numeric rules can share a rule set. `aggregate` defaults to `'sum'`, and is currently the only aggregate. `result.score` is always the total. When `threshold` is set and the total meets it, `result.matched` also lists the rules whose results were truthy; otherwise `result.matched` is empty.

### Decision validation

Before evaluation, each decision is checked against the schema: required fields present, types correct, constraints satisfied, custom type validators pass. Behaviour depends on `decisions_mode` set at `load_schema()`:

- `'loose'` (default): non-conforming fields are dropped and a warning is added to `result.warnings`. Evaluation proceeds on what remains. A rule that references a dropped field evaluates false.
- `'strict'`: any non-conforming decision raises `DecisionValidationError`.

Values are never coerced. `"600"` is not `600`.

### Semantics worth knowing

- A missing or dropped field makes any rule that references it false. `not missing_field = 1` is also false, because the error is raised inside the `not`.
- `and` and `or` short-circuit.
- Any exception inside a rule makes that rule false rather than failing the whole evaluation.
- Custom operators and schema functions run here and only here.

## Postgres

```python
from amino.backends.postgres import PostgresBackend

q = PostgresBackend().compile(expr)
q.sql     # '(("score" > %s) AND (position(%s IN "name") > 0))'
q.params  # [40, 'ob']

with conn.cursor() as cur:
    cur.execute(f"SELECT id FROM users WHERE {q.sql}", q.params)
```

Parameters are psycopg positional placeholders. List membership renders as `col = ANY(%s)` so a Python list binds as one array parameter. Identifiers are double-quoted.

## ClickHouse

```python
from amino.backends.clickhouse import ClickHouseBackend

q = ClickHouseBackend().compile(expr)
q.sql     # '((`score` > {p0:Int64}) AND (position(`name`, {p1:String}) > 0))'
q.params  # {'p0': 40, 'p1': 'ob'}

client.query(f"SELECT id FROM users WHERE {q.sql}", parameters=q.params)
```

Placeholders are ClickHouse server-side typed parameters. The type comes from the schema: `Int` binds as `Int64`, `Float` as `Float64`, `Str` as `String`, `Bool` as `Bool`, a list as `Array(T)`. Custom types bind as their base type. Identifiers are backtick-quoted.

## SQL targets: shared behaviour

### Operator rendering

| Expression | Postgres | ClickHouse |
|---|---|---|
| `= != < > <= >=` | same, `!=` becomes `<>` | same |
| `and or not` | `AND OR NOT`, every node parenthesised | same |
| `x in [..]` | `x = ANY(%s)` | `x IN {p:Array(T)}` |
| `x not in [..]` | `NOT (x = ANY(%s))` | `x NOT IN {p:Array(T)}` |
| `x in []`, `x not in []` | `FALSE`, `TRUE` | `FALSE`, `TRUE` |
| `x contains 'y'` | `position(%s IN x) > 0` | `position(x, {p:String}) > 0` |
| `fn(a, b)` | `fn(a, b)` | `fn(a, b)` |

Function calls are emitted by name and must exist in the target database. There is no name mapping. The function must also be declared in the schema; see [security.md](security.md#implementation-status) for the current state of that check.

### Column mapping

Top-level fields render as their quoted name. Nested struct fields have no default rendering and must be mapped. The mapping also covers tables whose column names differ from the schema.

```python
backend = PostgresBackend(columns={
    "customer.tier": "customer_tier",
    "score": "s.score",
})
```

Mapped values are spliced into the SQL verbatim. They are trusted fragments written by the developer, never user input.

### What raises

Backends never degrade silently. `UnsupportedExpressionError` is raised for:

- a nested field with no column mapping
- a custom operator registered with `register_operator()`
- `in` or `not in` whose right side is not a list literal
- a list literal anywhere other than the right of `in` or `not in`

### Divergence from the Python evaluator

These are defects to close, per [security.md](security.md) guarantee 6, and are listed so a deployer can avoid them today.

- **NULL.** SQL uses three-valued logic. `score > 5` on a NULL `score` is unknown, and `NOT` of unknown is still unknown, so the row is excluded either way. The Python evaluator makes a rule referencing a missing field false, which for `not` gives the opposite answer. Prefer `NOT NULL` columns for fields the DSL filters on.
- **String comparison.** Postgres follows the column's collation. ClickHouse compares bytes. Python compares code points. ASCII data behaves identically everywhere.

## Writing a target

### A SQL dialect

Subclass `amino.backends.SQLBackend` and implement four hooks. The tree walk, precedence, parenthesisation, membership handling, and error cases are inherited.

```python
from amino.backends import ParamSink, SQLBackend

class MyDialect(SQLBackend):
    def quote_ident(self, name: str) -> str: ...
    def new_params(self) -> ParamSink: ...
    def render_in(self, column: str, placeholder: str) -> str: ...
    def render_contains(self, haystack: str, needle: str) -> str: ...
```

`ParamSink.add(value, base_type)` binds one value and returns the placeholder text to splice in. `base_type` is one of `Int`, `Float`, `Str`, `Bool`, or `List[T]`. `ParamSink.result()` returns the parameters in whatever shape the driver wants. The Postgres backend is under forty lines; read it first.

### Anything else

Walk `Expression.ast` directly. The node types in `amino.rules.ast` are `Literal`, `Variable`, `UnaryOp`, `BinaryOp`, and `FunctionCall`, each carrying `type_name`. `Expression.base_type(name)` reduces a custom type to its primitive. Raise `UnsupportedExpressionError` for anything you cannot render; do not approximate.

Whatever you build, add it to the parity suite. A target that can disagree with the others on a supported expression is a target that hands users a footgun.

## Testing targets

`tests/integration/test_sql_parity.py` runs every expression in its list through Postgres, ClickHouse, and the Python evaluator against the same twelve rows and asserts all three select the same ids.

```bash
make db-up              # postgres:16 on :55432, clickhouse:24.8 on :18123
make test-integration
make db-down
```

`make test` runs the same tests and skips them when a database is unreachable. Override connection strings with `AMINO_PG_DSN` and `AMINO_CH_URL`. Drivers are optional extras: `amino[postgres]` and `amino[clickhouse]`. The backends import neither; only your code and the tests do.
