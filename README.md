# amino

A small expression language for building the features where your users write conditions over your data: rules engines, query languages, feature targeting, policies, alerts.

```
credit_score < 600 and state_code in ['CA', 'NY']
```

You define a schema. Your users write expressions like that one against it. Amino checks each expression against the schema, then compiles it for wherever it needs to run: in-process Python, a Postgres `WHERE` clause, a ClickHouse `WHERE` clause, or a target you write. Build the feature; don't build the language.

## Why

Plenty of features come down to a condition written by someone who is not an engineer. Which users see a flag. Which rows a policy allows. Which tickets a saved search returns. Which orders get routed to review. Each time, someone has to build the little language those conditions are written in, and each time it is built under deadline, slightly differently, and never quite finished.

Amino is that language, built once, so the feature on top of it can be small. It comes with the requirements those features share already met:

- **Checked against a schema.** An expression can only name fields, functions, and operators you declared. Unknown names are rejected before anything runs.
- **Safe to accept from people you don't trust.** Nothing a user types executes. Literals are bound as parameters. The language has no loops, assignment, or way to reach past the schema, so it can be exposed to the internet. See [docs/security.md](docs/security.md) for the guarantees and their current status.
- **Runs in more than one place.** The same expression decides for one record in process and selects all matching records in the database, with a test suite that keeps the answers identical.
- **Small enough to reimplement.** Two grammar files. A TypeScript host for composing and validating in the browser is planned.

It borrows GraphQL's central move, a schema that decides what a client can say, and points it at a different problem. GraphQL lets clients choose which fields come back. Amino lets users choose which records do.

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

Yes, if you are building a feature where users express a condition over records you control: a rules engine, a saved-search or query box, feature targeting, row-level policy, alert conditions, data quality checks, routing. Especially if the same condition has to run in more than one place.

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
