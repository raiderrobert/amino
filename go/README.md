# amino for Go

A full host implementation: parse, type-check, evaluate in process, and compile to Postgres and ClickHouse. It passes every case in [`../spec/conformance/`](../spec/conformance/README.md), including the ones the Python reference implementation still marks as expected failures.

Standard library only. Module path `github.com/raiderrobert/amino/go`.

```bash
go get github.com/raiderrobert/amino/go
```

## Use

```go
import (
    amino "github.com/raiderrobert/amino/go"
    "github.com/raiderrobert/amino/go/backend"
)

engine, err := amino.LoadSchema(`
credit_score: Int
state_code: Str
income: Int
`)

// As a rules engine: hold the rules fixed, stream records past them.
result, err := engine.Eval(
    []amino.Rule{{ID: "decline", Expr: "credit_score < 600 and state_code in ['CA', 'NY']"}},
    map[string]any{"credit_score": 580, "state_code": "CA", "income": 45000},
    nil,
)
result.Matched // ["decline"]

// As a query language: parse once, compile for the store.
expr, err := engine.Parse("credit_score < 600 and state_code in ['CA', 'NY']")
q, err := backend.Postgres{}.Compile(expr)
q.SQL    // (("credit_score" < $1) AND ("state_code" = ANY($2)))
q.Params // []any{int64(600), []any{"CA", "NY"}}
rows, err := db.Query(ctx, "SELECT id FROM applications WHERE "+q.SQL, q.Params.([]any)...)
```

For repeated evaluation, `engine.Compile(rules, match)` returns a `*CompiledRules` with `Eval` and `EvalOne`. Match modes (`all`, `first`, `inverse`, `score`) are set with `*amino.MatchConfig` exactly as documented in [`../docs/targets.md`](../docs/targets.md#match-modes).

## Configuration

Everything is set at construction with options, and the engine is immutable and safe for concurrent use after that. There is no freeze step.

```go
engine, err := amino.LoadSchema(schemaText,
    amino.WithFunction("toxicity", func(args ...any) (any, error) { ... }),
    amino.WithType("sku", "Str", isSKU),
    amino.WithOperator(amino.OperatorDef{
        Keyword: "near", BindingPower: 40, InputTypes: []string{"Int", "Int"}, ReturnType: "Bool",
        Fn: func(args ...any) (any, error) { ... },
    }),
    amino.WithOperators("minimal"),            // or WithOperatorList("=", "!=")
    amino.WithDecisionsMode("strict"),         // default "loose"
    amino.WithMaxDepth(100), amino.WithMaxLength(10000),
)
```

## Errors

Every error is an `*amino.Error` with a `Code`. The parse-time codes are the corpus's named validation rules, so an application can map them to messages or HTTP statuses without parsing text:

```go
var ae *amino.Error
if errors.As(err, &ae) {
    switch ae.Code {
    case amino.CodeUnknownField, amino.CodeTypeMismatch, amino.CodeSyntax: // user's mistake
    case amino.CodeDepthExceeded:                                          // limit hit
    }
}
```

## Where this host differs from Python

These are deliberate, and each one is the specification rather than the Python behaviour:

- **Undeclared functions are parse errors** (`unknown_function`). Python currently accepts them and its SQL backends emit them verbatim.
- **Built-in comparisons are type-checked** (`type_mismatch`). `name = 5` on a `Str` field is rejected. Python currently accepts it.
- **Length and depth limits are on by default.** Python has none yet.
- **Truncated input is a `syntax` error.** Python raises a bare `IndexError`.
- **Custom type validators run during record validation.** Python's `DecisionValidator` does not call them.
- **Postgres placeholders are `$1, $2`** for pgx and database/sql, not psycopg's `%s`. The SQL is otherwise byte-identical to Python's, and the tests assert that.
- **Options instead of registration methods.** No `register_*` calls, no `EngineAlreadyFrozenError`.

Rule ids are strings. Record ids are whatever the record's `id` key holds.

## Layout

```
*.go               package amino: schema, parser, type checking, evaluator, matcher, options
backend/           package backend: Dialect interface, shared compiler, Postgres, ClickHouse
conformance_test.go runs ../spec/conformance; cases marked "go: ..." are expected failures here
```

## Develop

Go 1.22 or newer.

```bash
cd go
go test ./...
go vet ./... && gofmt -l .
```

Or `make test-go` from the repository root. There is no live-database parity suite for this host yet; the backends are held to Python's SQL by exact-string tests, and Python's parity suite holds that SQL to the databases.
