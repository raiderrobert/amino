# amino

A small expression language for building the features where your users write conditions over your data: rules engines, query languages, feature targeting, policies, alerts.

```
credit_score < 600 and state_code in ['CA', 'NY']
```

You define a schema. Your users write expressions like that one against it. Amino checks each expression against the schema, then compiles it for wherever it needs to run: in your application, in your database, or in a target you write. Build the feature; don't build the language.

## Why

Plenty of features come down to a condition written by someone who is not an engineer. Which users see a flag. Which rows a policy allows. Which tickets a saved search returns. Which orders get routed to review. Each time, someone has to build the little language those conditions are written in, and each time it is built under deadline, slightly differently, and never quite finished.

Amino is that language, built once, so the feature on top of it can be small. It comes with the requirements those features share already met:

- **Checked against a schema.** An expression can only name fields, functions, and operators you declared. Unknown names are rejected before anything runs.
- **Safe to accept from people you don't trust.** Nothing a user types executes, and the language has no loops, assignment, or way to reach past the schema. See [docs/security.md](docs/security.md).
- **Runs in more than one place.** The same expression decides for one record in process and selects all matching records in the database, with a test suite that keeps the answers identical.
- **Small enough to reimplement.** Two grammar files and a conformance corpus. There are Python, Go, and TypeScript hosts, and the TypeScript one validates in the browser as the user types.

It borrows GraphQL's central move, a schema that decides what a client can say, and points it at a different problem. GraphQL lets clients choose which fields come back. Amino lets users choose which records do.

## What it looks like

One schema, one expression, two features.

```python
import amino

engine = amino.load_schema("""
credit_score: Int
state_code: Str
income: Int
""")
```

**As a rules engine.** Hold the rules fixed, stream records past them, get a verdict for each.

```python
result = engine.eval(
    rules=[{"id": "decline", "rule": "credit_score < 600 and state_code in ['CA', 'NY']"}],
    decision={"credit_score": 580, "state_code": "CA", "income": 45000},
)
result.matched   # ['decline']
```

**As a query language.** Hold the dataset fixed, push one expression into it, get back the records that match.

```python
from amino.backends.postgres import PostgresBackend   # or ClickHouseBackend, or a dialect you write

expr = engine.parse("credit_score < 600 and state_code in ['CA', 'NY']")

q = PostgresBackend().compile(expr)
q.sql      # '(("credit_score" < %s) AND ("state_code" = ANY(%s)))'
q.params   # [600, ['CA', 'NY']]

cur.execute(f"SELECT id FROM applications WHERE {q.sql}", q.params)
```

Same text, same parse, opposite direction. Which backend compiles the expression is one line, so one query box can front several stores, and a rule evaluated in the application and a query run in the database cannot drift apart. See [docs/targets.md](docs/targets.md) for the targets and for writing your own.

**Across client and server.** The browser checks the expression as the user types, against the same schema the server uses. The TypeScript host does the checking in the browser; the server parses the text again when it arrives.

```ts
// browser
import { loadSchema } from "@raiderrobert/amino";

const engine = loadSchema(await fetch("/api/search/schema").then((r) => r.text()));

input.oninput = () => {
  const check = engine.validate(input.value);
  hint.textContent = check.ok ? "" : check.error.message;   // 'unknown_field: unknown field "stat"'
};
form.onsubmit = () => fetch("/api/search", { method: "POST", body: input.value });
```

```python
# server
@app.get("/api/search/schema")
def schema():
    return engine.export_schema()          # the same .amn text the browser loads

@app.post("/api/search")
def search(text: str):
    expr = engine.parse(text)              # parse on arrival, then compile for the store
    q = PostgresBackend().compile(expr)
    return db.execute(f"SELECT id FROM applications WHERE {q.sql}", q.params)
```

The Python, Go, and TypeScript hosts are held to one conformance corpus, so browser and server share one definition of a valid expression and one set of error codes. The user sees a mistake before the round trip.

## Is it for you

Yes, if you are building a feature where users express a condition over records you control: a rules engine, a saved-search or query box, feature targeting, row-level policy, alert conditions, data quality checks, routing. Especially if the same condition has to run in more than one place.

No, if you need projections, sorting, aggregation, sequencing, or anything with side effects. Amino says which records qualify and nothing else. Those are boundaries, not a roadmap.

## Status

Early, and used by one person. The API is small and may change.

Not on PyPI yet:

```bash
pip install "git+https://github.com/raiderrobert/amino.git#subdirectory=python"
```

Python 3.10 or newer. Database drivers are optional extras, `amino[postgres]` and `amino[clickhouse]`, and are only needed to execute what a backend produces. The Python package is the reference implementation. Go and TypeScript hosts exist and pass the same conformance corpus. See [ADR 006](docs/adr/006-repository-layout-for-multiple-hosts.md).

## Learn more

Start with [docs/README.md](docs/README.md), which orders the rest. The short version:

- [What amino is for and what that requires](docs/adr/005-one-language-for-user-written-conditions.md), including the GraphQL comparison
- [Security model](docs/security.md): the threat model, the guarantees, and their current status
- [Expression language](docs/expression-language.md) and [schema language](docs/schema-language.md)
- [Targets](docs/targets.md): the Python evaluator with match modes, Postgres, ClickHouse, and writing your own
- [Python API reference](python/API.md)
- [Development](DEVELOPMENT.md), and the [conformance corpus](spec/conformance/README.md) every host must pass

MIT licensed.
