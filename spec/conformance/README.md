# Conformance Corpus

Every host implementation of amino must pass every case in this directory. The corpus is the executable half of the specification; the grammars in `../grammar/` are the other half. A host that passes the corpus and implements the grammars is a conforming amino implementation.

The reference implementation is Python. When Python and the corpus disagree, one of them has a bug, and it is decided case by case which. A case that the reference implementation is known to fail carries `"xfail"` with a reason, so the corpus can describe required behaviour ahead of any implementation.

## Files

- `parse/*.json`: does an expression parse against a schema, and if so with what result type, and if not with what error?
- `eval/*.json`: given a schema, records, and expressions, which records match? This is the semantics the Python evaluator and every SQL target must agree on.

Each file is self-contained: it carries its own schema so a host can run one file in isolation.

## Parse case format

```json
{
  "schema": "score: Int\nname: Str",
  "cases": [
    {"name": "int comparison", "expression": "score > 5", "expect": "accept", "type": "Bool"},
    {"name": "unknown field",  "expression": "missing > 5", "expect": "reject", "error": "unknown_field"},
    {"name": "undeclared fn",  "expression": "f(score) = 1", "expect": "reject", "error": "unknown_function",
     "xfail": "python: parser accepts undeclared functions; ADR 005 consequence 2"}
  ]
}
```

- `expect` is `accept` or `reject`.
- `type` on an accept is the result type of the root: `Bool`, `Int`, `Float`, or `Str`.
- `error` on a reject is a named validation rule from the table below. A host maps it to its own error class.
- `operators`, if present at file level, is the operator preset the engine is built with. Default `standard`.
- `xfail`, if present, is a string explaining why one host currently fails this case. It is prefixed with that host's name: `python: ...`, `go: ...`, `typescript: ...`. A host treats a case as an expected failure only when the prefix is its own; every other host must pass it. This is how the corpus describes required behaviour that the reference implementation does not have yet.

## Named validation rules

| `error` | Meaning | Python error class |
|---|---|---|
| `syntax` | The text is not a well-formed expression. | `RuleParseError` |
| `unknown_field` | An identifier does not name a field in the schema. | `RuleParseError` |
| `unknown_function` | A call names a function the schema does not declare. | `RuleParseError` (pending) |
| `unknown_operator` | An operator token has no registration for the operand types. | `RuleParseError` |
| `type_mismatch` | Operands are of incompatible types for a built-in operator. | `TypeMismatchError` (pending) |
| `depth_exceeded` | Nesting is deeper than the host's limit. | (pending) |

"Pending" marks rules the Python reference implementation does not yet enforce. Cases for them carry `xfail: "python: ..."`. The Go host enforces all six.

## Eval case format

```json
{
  "schema": "id: Int\nscore: Int\nname: Str",
  "records": [
    {"id": 1, "score": 10, "name": "alice"},
    {"id": 2, "score": 50, "name": "bob"}
  ],
  "cases": [
    {"expression": "score > 20", "matches": [2]},
    {"expression": "name contains 'a'", "matches": [1]}
  ]
}
```

- Every record has an integer `id`.
- `matches` is the sorted list of ids for which the expression is true.
- Records may be nested to match struct fields in the schema. A host with only SQL targets maps dotted paths to columns.
- Records contain no nulls and no optional fields, because SQL three-valued logic and the Python evaluator differ there and that divergence is not yet resolved (ADR 005, open questions). When it is, cases will be added.
- A host with an in-process evaluator runs these directly. A host with only SQL targets loads the records into a database and runs `SELECT id ... WHERE <compiled>`.

## Running

Python: `cd python && uv run pytest tests/test_conformance.py`. Go: `cd go && go test -run Conformance ./...`. Each host's runner reads this directory directly; the corpus is never copied.

## Adding cases

Add the case to the corpus first, then make the reference implementation pass it. A grammar change is not complete until the corpus has cases that fail on the old grammar and pass on the new one.
