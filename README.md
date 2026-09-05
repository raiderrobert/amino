# amino

A small expression language you can safely let strangers write against your data.

```
credit_score < 600 and state_code in ['CA', 'NY']
```

You define a schema. Your users write expressions like that one against it. Amino checks each expression against the schema, then compiles it for wherever it needs to run: in-process Python, a Postgres `WHERE` clause, a ClickHouse `WHERE` clause, or a target you write. The same text, the same meaning, everywhere.

## Why

Plenty of systems need a condition written by someone who is not an engineer. Which users see a feature. Which rows a policy allows. Which tickets a saved search returns. Which orders get flagged. The usual choices are a form that can't express enough, a scripting language that can express far too much, or a mini-language invented under deadline and never quite safe.

Amino is the mini-language, done once. It is deliberately tiny: comparisons, `and`/`or`/`not`, list membership, substring match, dot paths into structs, and calls to functions the developer declared. No loops, no assignment, no way to reach anything the schema didn't expose. That is what makes it safe to accept from the internet, and small enough to implement in more than one language.

It borrows GraphQL's central move, a schema that decides what a client can say, and points it at a different problem. GraphQL lets untrusted clients choose which fields come back. Amino lets untrusted users choose which records do.

## What it looks like

```python
import amino
from amino.backends.postgres import PostgresBackend

engine = amino.load_schema("""
credit_score: Int
state_code: Str
income: Int
""")

expr = engine.parse("credit_score < 600 and state_code in ['CA', 'NY']")

# Decide for one record, in process
engine.eval(
    rules=[{"id": "decline", "rule": "credit_score < 600 and state_code in ['CA', 'NY']"}],
    decision={"credit_score": 580, "state_code": "CA", "income": 45000},
).matched                                   # ['decline']

# Select every matching record, in the database
q = PostgresBackend().compile(expr)
q.sql                                       # '(("credit_score" < %s) AND ("state_code" = ANY(%s)))'
q.params                                    # [600, ['CA', 'NY']]
```

Everything the user typed is bound as a parameter. Nothing is interpolated.

## Is it for you

Yes, if an untrusted person needs to express a condition over records you control, and especially if that condition has to run in more than one place. Feature targeting, row-level policy, alert conditions, data quality checks, saved searches, routing rules.

No, if you need projections, sorting, aggregation, sequencing, or anything with side effects. Amino says which records qualify and nothing else. Those are boundaries, not a roadmap.

## Status

Early, and used by one person. The API is small and may change. Two known gaps in the safety guarantees are documented in [docs/security.md](docs/security.md) and are scheduled before any new feature. Read that page before exposing amino to untrusted input.

Not on PyPI yet:

```bash
pip install git+https://github.com/raiderrobert/amino.git
```

Python 3.10 or newer. Database drivers are optional extras, `amino[postgres]` and `amino[clickhouse]`, and are only needed to execute what a backend produces.

## Learn more

Start with [docs/README.md](docs/README.md), which orders the rest. The short version:

- [Why amino is shaped this way](docs/adr/005-safe-expression-language-for-untrusted-users.md), including the GraphQL comparison
- [Security model](docs/security.md): the threat model, the guarantees, and their current status
- [Expression language](docs/expression-language.md) and [schema language](docs/schema-language.md)
- [Targets](docs/targets.md): the Python evaluator with match modes, Postgres, ClickHouse, and writing your own
- [API reference](docs/api.md)
- [Development](DEVELOPMENT.md)

MIT licensed.
