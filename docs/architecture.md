# Architecture

## What amino is

Amino is a small expression language for building features in which users write conditions over a developer's data: rules engines, query languages, targeting, policy, alerting. It is one fixed grammar; its vocabulary comes from a developer-defined schema; it is safe to accept from untrusted users. An expression is parsed and type-checked once, then handed to a target that turns it into something executable: an in-process Python callable, a Postgres predicate, a ClickHouse predicate, or a backend the developer writes. [ADR 005](adr/005-one-language-for-user-written-conditions.md) records why.

The Python package is the reference implementation. Its behaviour is the specification that other host implementations must match.

## Pipeline

```
Schema text ──▶ Schema Parser ──▶ SchemaAST ──▶ Schema Validator ──▶ SchemaRegistry
                (static PEG)                    (refs, cycles,         (lookup, export)
                                                 duplicates)                 │
                                                                             │
   register_type()      ──▶ TypeRegistry      ─┐                             │
   register_operator()  ──▶ OperatorRegistry  ─┤  frozen at first parse      │
   add_function()       ──▶ functions dict    ─┘                             │
                                                                             ▼
Expression text ──▶ Pratt parser ──▶ typed RuleAST ──▶ Expression
                    (dynamic op table,                     │
                     types from schema)                    │
                                                           ├──▶ TypedCompiler ──▶ CompiledRules ──▶ eval(decisions)
                                                           │    (Python target)     + DecisionValidator
                                                           │                        + Matcher ──▶ MatchResult
                                                           │
                                                           ├──▶ PostgresBackend   ──▶ Query(sql, params)
                                                           ├──▶ ClickHouseBackend ──▶ Query(sql, params)
                                                           └──▶ your SQLBackend   ──▶ Query(sql, params)
```

Everything above the `Expression` line is shared. Everything below it is a target.

## Three things with three lifetimes

- **Schema.** Fields, types, structs, constraints, function signatures. Fixed for the life of an engine. Changing it means building a new engine.
- **Expressions.** The text users write. Parsed against the schema. Cheap, frequent, replaceable at any time. The Python target calls them rules.
- **Records.** The data an expression is applied to. Always dynamic, never retained. The Python target calls them decisions; SQL targets never see them, the database does.

They are separated because they change at different rates. A schema change can invalidate every compiled expression that references the changed field, so schema and expressions cannot be independently swapped in the general case. Fixing the schema per engine removes that class of bug and lets types resolve at parse time against something stable.

## Rules and queries are one thing

A rule holds the expression fixed and streams records past it. A query holds the dataset fixed and pushes one expression into it. The same text is either, depending on which side is the constant. The difference is entirely in the target: batch-and-match in process, or compile-to-the-store's-language. The grammar does not know which it is.

## Engine lifecycle

```
Construction  │  load_schema() parses and validates the schema, sets modes and operator preset
              │
Registration  │  register_type(), register_operator(), add_function()
              │
  ── Freeze ──┘  First parse(), compile(), or eval() freezes all registries.
                 Later registration raises EngineAlreadyFrozenError.
                 Expressions may be parsed and compiled indefinitely after this.

  ── Replace     Schema change: build a new Engine, drain work against the old one, discard it.
```

Freezing exists because parsing resolves operators and types from the registries. A registry that could change under a parsed expression would make the expression's meaning unstable.

There is no in-place rule update. `compile()` returns an immutable `CompiledRules`; to change the rule set, compile again and swap the reference. Schema changes are handled by atomic engine replacement: the application builds a new engine, drains in-flight work against the old one, and discards it. Amino makes one engine well-encapsulated and replaceable. The application decides when to swap.

## Multi-context is the application's job

A context is a (schema, expressions, validation modes) tuple. Serving several at once, such as one schema per tenant or one per trust level, is done by holding several engines and routing to the right one. Amino has no naming, routing, or lifecycle API for this. Exposing a narrower schema to a less trusted population is also how authorization scoping is done; see [security.md](security.md).

## Text is the interchange format

Expressions are stored and transmitted as text. There is no serialised AST or binary form. Every host implementation parses independently. The portable unit is the (schema, expression) pair: `credit_score < 600` has no meaning without knowing `credit_score` is an `Int`.

This is [ADR 002](adr/002-dsl-interchange-format-and-multi-language.md). Its consequences:

- Every host needs a parser and a type checker, and they must accept and reject the same inputs. A shared conformance corpus will enforce this.
- `engine.export_schema()` returns the schema in `.amn` text. A JSON form carrying operator signatures is planned so a host can validate a custom operator it cannot execute.
- A TypeScript implementation of parse and validate is planned for composing expressions in the browser. The server re-parses regardless; browser validation is a convenience, not a boundary.

## Error hierarchy

```
AminoError
├── SchemaParseError            syntax error in .amn text
├── SchemaValidationError       unknown type reference, circular struct, duplicate name
├── RuleParseError              syntax error or unknown field in an expression
├── TypeMismatchError           reserved; not currently raised (see expression-language.md)
├── DecisionValidationError     record fails schema or constraints in strict decisions mode
├── RuleEvaluationError         runtime error inside the Python target
├── UnsupportedExpressionError  a target cannot render part of an expression
├── OperatorConflictError       duplicate operator registration
└── EngineAlreadyFrozenError    registration after first use
```

Every error carries `message`, and where it applies, `field`, `expected`, and `got`.

## Package layout

```
amino/
├── __init__.py            load_schema(), public exports
├── engine.py              Engine: registries, freeze, parse(), compile(), eval()
├── expression.py          Expression: typed AST plus the registries a target needs
├── errors.py
├── schema/
│   ├── parser.py          static PEG parser for .amn
│   ├── ast.py
│   ├── validator.py       references, cycles, duplicates
│   └── registry.py        field lookup by dotted path, export
├── rules/
│   ├── parser.py          Pratt parser; dynamic operator table; types from schema
│   ├── ast.py             Literal, Variable, UnaryOp, BinaryOp, FunctionCall, RuleAST
│   └── compiler.py        TypedCompiler: AST to Python closure (Python target)
├── operators/
│   ├── registry.py        OperatorDef, OperatorRegistry
│   └── standard.py        'standard' and 'minimal' presets
├── types/
│   ├── registry.py        TypeRegistry: name to base type plus validator
│   └── builtin.py         ipv4, ipv6, cidr, email, uuid
├── runtime/               the Python target
│   ├── compiled_rules.py  CompiledRules
│   ├── validator.py       DecisionValidator: schema, constraints, custom types
│   ├── evaluator.py
│   └── matcher.py         all / first / inverse / score
└── backends/              SQL targets
    ├── base.py            Query, ParamSink, SQLBackend (shared tree walk)
    ├── postgres.py
    └── clickhouse.py
```

The Python evaluator under `runtime/` is planned to move under `backends/` so the package layout says what the architecture says: one parser, many targets.
