# amino

A toolkit for building a small, typed expression language over your data and compiling it to more than one place.

You write the schema once. Your users write expressions against it. Amino parses and type-checks each expression once, then hands the result to whichever target needs to run it: in-process Python, a Postgres `WHERE` clause, a ClickHouse `WHERE` clause, or a backend you write yourself.

```
credit_score < 600 and state_code in ['CA', 'NY']
```

That one line, checked against a schema that says `credit_score` is an `Int` and `state_code` is a `Str`, becomes:

| Target | Output |
|---|---|
| Python | a callable you run over dicts, with batch evaluation and match modes |
| Postgres | `(("credit_score" < %s) AND ("state_code" = ANY(%s)))` with `[600, ['CA', 'NY']]` |
| ClickHouse | `` ((`credit_score` < {p0:Int64}) AND (`state_code` IN {p1:Array(String)})) `` with `{'p0': 600, 'p1': ['CA', 'NY']}` |

The parser and type checker are shared. A target is only the part that differs.

## When this is the right tool

You have a filter, rule, or search language that people other than you need to write, and you need it to run in more than one place. The recurring shape:

- **One search box, several stores.** Product, analytics, and audit data live in different databases. Users learn one syntax. Each request is compiled for whichever store answers it.
- **Rules that engineers don't own.** Pricing, eligibility, routing, moderation. Non-engineers edit them, often. They need to be checked before they run, not discovered broken in production.
- **The same predicate at two speeds.** Evaluate a rule in-process against one record, or push it down as SQL to select every matching record. Same text, same meaning.

If you need a full query language with projections, joins, sorting, and aggregation, amino is not that. It compiles predicates.

## How it works

```
schema text ──▶ Schema Registry ──┐
                                  ├──▶ typed Expression ──▶ target ──▶ output
expression text ──▶ Pratt parser ─┘         │
                                            ├── Python evaluator     callable + MatchResult
                                            ├── PostgresBackend      (sql, params)
                                            ├── ClickHouseBackend    (sql, params)
                                            └── your SQLBackend      (sql, params)
```

Three things with three different lifetimes:

- **Schema** defines fields, types, structs, constraints, and function signatures. Fixed for the life of an engine.
- **Expressions** are the text users write. Parsed and type-checked against the schema. Cheap, frequent, hot-swappable.
- **Targets** turn a typed expression into something executable. Each target decides what it can render and raises on anything it can't. No silent degradation.

Because typing happens before any target sees the expression, a target can rely on `credit_score` being an `Int` when it picks a parameter type, and an expression that references a field the schema doesn't have never reaches a database at all.

## Install

Not on PyPI yet. Install from the repository:

```bash
pip install git+https://github.com/raiderrobert/amino.git
```

Database drivers are optional extras and are only needed if you execute the SQL a backend produces:

```bash
pip install "amino[postgres] @ git+https://github.com/raiderrobert/amino.git"     # psycopg
pip install "amino[clickhouse] @ git+https://github.com/raiderrobert/amino.git"   # clickhouse-connect
```

Requires Python 3.10 or newer.

## Quick start

A schema file, `applications.amn`:

```
amount: Int
state_code: Str
credit_score: Int {min: 300, max: 850}
income: Int
```

Parse one expression and compile it three ways:

```python
import amino
from amino.backends.postgres import PostgresBackend
from amino.backends.clickhouse import ClickHouseBackend

engine = amino.load_schema("applications.amn")
expr = engine.parse("credit_score < 600 and state_code in ['CA', 'NY']")

# In-process, against a dict
result = engine.eval(
    rules=[{"id": "decline", "rule": "credit_score < 600 and state_code in ['CA', 'NY']"}],
    decision={"amount": 75000, "state_code": "CA", "credit_score": 580, "income": 45000},
)
result.matched  # ['decline']

# Postgres
q = PostgresBackend().compile(expr)
cur.execute(f"SELECT id FROM applications WHERE {q.sql}", q.params)

# ClickHouse
q = ClickHouseBackend().compile(expr)
client.query(f"SELECT id FROM applications WHERE {q.sql}", parameters=q.params)
```

Literals the user typed are always bound as parameters. They are never spliced into SQL.

`engine.parse()` freezes the engine, the same as `compile()` and `eval()` do. Register custom types and operators before the first call.

## Targets

### Python evaluator

The in-process target is the original rules engine. It evaluates one or many rules against one or many records and aggregates the results with a match mode:

```python
compiled = engine.compile(
    rules=[
        {"id": "high_risk",   "rule": "credit_score < 500",                   "ordering": 1},
        {"id": "ca_income",   "rule": "state_code = 'CA' and income < 50000",  "ordering": 2},
        {"id": "amount_risk", "rule": "credit_score < 650 and amount > 40000", "ordering": 3},
    ],
    match={"mode": "first", "key": "ordering", "order": "asc"},
)

results = compiled.eval([
    {"id": "app_1", "amount": 45000, "state_code": "CA", "credit_score": 480, "income": 55000},
    {"id": "app_2", "amount": 65000, "state_code": "TX", "credit_score": 720, "income": 80000},
])
# app_1 → matched: ['high_risk']   (first match by ordering)
# app_2 → matched: []
```

Match modes: `all` (default), `first` by an ordering key, `inverse` (rules that did not match), and `score` (aggregate numeric or boolean results with a threshold). See [docs/rule-expression.md](docs/rule-expression.md).

Schema-declared functions are implemented in Python and passed at load time, so a rule can call into an ML model or an external service:

```
toxicity_score: (text: Str) -> Float
```

```python
engine = amino.load_schema("schema.amn", funcs={"toxicity_score": model.predict})
```

### Postgres and ClickHouse

Both compile an expression to a parameterised predicate. Postgres binds psycopg-style positional `%s` parameters and renders list membership as `col = ANY(%s)`. ClickHouse binds server-side typed `{p0:Int64}` parameters, with the type taken from the schema.

Nested struct fields and renamed columns are handled with a mapping:

```python
backend = PostgresBackend(columns={"customer.tier": "customer_tier", "score": "s.score"})
```

Function calls are emitted by name and must exist in the target database. Operators registered with a Python function only run on the Python target; the SQL targets raise `UnsupportedExpressionError` for them.

SQL uses three-valued logic and the Python evaluator does not, so expressions over nullable columns can select different rows on different targets. [docs/backends.md](docs/backends.md) covers this and the rest of the operator rendering table.

### Writing a target

Subclass `amino.backends.SQLBackend` and implement four hooks: identifier quoting, a parameter sink, list membership, and substring search. The tree walk, operator precedence, and error handling are inherited. The Postgres backend is about forty lines.

A non-SQL target walks `Expression.ast` directly. The node types are `Literal`, `Variable`, `UnaryOp`, `BinaryOp`, and `FunctionCall`, each carrying its resolved type name.

## Schema language

Fields are `name: Type`. Comments use `#`. Files use the `.amn` extension by convention.

```
amount: Int
state_code: Str
credit_score: Int {min: 300, max: 850}
tags: List[Str]
email: Str?                      # optional
contact: email                   # custom type, registered in Python

struct Address { street: Str, city: Str, country: Str }
struct Customer { id: Str, billing: Address, shipping: Address? }
customer: Customer               # customer.billing.city in expressions

calculate_discount: (tier: Str, amount: Float) -> Float
```

Primitives are `Int`, `Float`, `Str`, `Bool`. Constraints (`min`, `max`, `minLength`, `pattern`, `oneOf`, and others) are enforced when the Python target validates a record. Custom types are registered with a base primitive and a validator:

```python
engine.register_type("email", base="Str", validator=is_email)
```

Full reference: [docs/schema-language.md](docs/schema-language.md). Formal grammars: [docs/grammar/](docs/grammar/).

## Expression language

Comparisons `= != < > <= >=`, boolean `and or not`, membership `in` and `not in` against a list literal, and `contains` for substrings. Function calls use `name(arg, arg)`. Struct fields use dot notation. String literals use single quotes.

Custom operators are registered with a binding power and input types, and take part in type checking:

```python
engine.register_operator(
    keyword="precedes", fn=event_precedes, binding_power=40,
    input_types=("Str", "Str"), return_type="Bool",
)
```

Full reference: [docs/rule-expression.md](docs/rule-expression.md).

## Non-goals

- **Not a query language.** No projections, joins, ordering, pagination, or aggregation. Amino produces the predicate; you write the `SELECT` around it.
- **Not a general-purpose language.** No variables, loops, or user-defined functions in the DSL. Logic that needs those belongs in a schema-declared function implemented in the host language.
- **Not a multi-language runtime.** Python is the only implementation. Earlier plans for independent runtimes in other languages are retired.

## Status

Early and used by one person. The public surface is small and may still change. The parity suite in `tests/integration/` runs every supported expression through Postgres, ClickHouse, and the Python evaluator against the same rows and requires all three to agree, so the targets are at least consistent with each other.

The `examples/` directory predates the current API and is being reworked.

## Development

```bash
git clone https://github.com/raiderrobert/amino.git
cd amino
make install-dependencies
make test                 # unit tests; integration tests skip without databases
make db-up                # postgres:16 on :55432, clickhouse:24.8 on :18123 via Docker
make test-integration     # the parity suite against both databases
make db-down
```

See [DEVELOPMENT.md](DEVELOPMENT.md).

## Documentation

- [Backends](docs/backends.md) — `parse()`, the SQL targets, column mapping, semantics that differ per target
- [Architecture](docs/architecture.md) — pipeline, engine lifecycle, design intent
- [Schema Language](docs/schema-language.md) — field types, structs, constraints, custom types
- [Expression Language](docs/rule-expression.md) — operators, match modes, custom operators
- [API Reference](docs/api.md) — public API
- [Decision records](docs/adr/) — why the system is shaped the way it is
