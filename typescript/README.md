# amino for TypeScript

Parse, type-check, and evaluate amino expressions in the browser or in Node. Zero runtime dependencies. It passes every case in [`../spec/conformance/`](../spec/conformance/README.md), including the ones the Python reference implementation still marks as expected failures.

Not published yet. Install from the repository:

```bash
pnpm add github:raiderrobert/amino#path:typescript
```

## What it is for

The first job is feedback while the user types. A search box or a rules editor calls `validate()` on every change and shows the error before anything is sent anywhere. The backend still re-parses; browser validation is a convenience, not a security boundary.

```ts
import { loadSchema } from "@raiderrobert/amino";

const engine = loadSchema(`
credit_score: Int
state_code: Str
income: Int
`);

const result = engine.validate(input.value);
if (!result.ok) {
  showError(result.error.code, result.error.message); // "unknown_field", "type_mismatch", ...
}
```

`validate()` never throws. `parse()` does the same work and throws an `AminoError` instead.

The schema comes from the backend. Fetch `engine.export_schema()` from the Python or Go service and pass the text to `loadSchema()` so the browser validates against exactly what the server will accept.

## As a full host

The in-process evaluator is included, so a Node service can be a complete host:

```ts
// As a rules engine: hold the rules fixed, stream records past them.
const verdict = engine.eval(
  [{ id: "decline", expr: "credit_score < 600 and state_code in ['CA', 'NY']" }],
  { credit_score: 580, state_code: "CA", income: 45000 },
);
verdict.matched; // ["decline"]

// Compile once for many records, with a match mode.
const compiled = engine.compile(rules, { mode: "first", key: "ordering", order: "asc" });
for (const r of compiled.eval(records)) r.matched;
```

Match modes (`all`, `first`, `inverse`, `score`) behave as documented in [`../docs/targets.md`](../docs/targets.md#match-modes). There are no SQL targets in this host yet; that is a separate decision, since the browser has no database and Node services can use the Python or Go targets' SQL over the wire.

## Configuration

Everything is set at construction and the engine is immutable after:

```ts
const engine = loadSchema(schemaText, {
  functions: { toxicity: (text) => model.score(text as string) },
  types: [{ name: "sku", base: "Str", validator: isSKU }],
  customOperators: [
    { keyword: "near", bindingPower: 40, inputTypes: ["Int", "Int"], returnType: "Bool", fn: (a, b) => ... },
  ],
  operators: "minimal",           // or ["=", "!="]; and/or/not are always on
  decisionsMode: "strict",        // default "loose"
  maxDepth: 100,
  maxLength: 10000,
});
```

A custom operator's `fn` only matters for evaluation. To validate an expression that uses an operator the server executes, register it here with its signature and no `fn`.

## Errors

Every failure is an `AminoError` with a `code`. Parse-time codes are the corpus's named validation rules:

| code | meaning |
|---|---|
| `syntax` | not a well-formed expression |
| `unknown_field` | identifier is not in the schema |
| `unknown_function` | call to an undeclared function |
| `unknown_operator` | operator not enabled in this preset |
| `type_mismatch` | operands or arguments of incompatible types |
| `depth_exceeded` | nesting past the limit |

## Where this host differs from Python

Each of these is the specification rather than the Python behaviour:

- Undeclared functions and mismatched built-in comparisons are parse errors. Python accepts them today.
- Length and depth limits are on by default. Python has none yet.
- Truncated input is a `syntax` error. Python raises a bare `IndexError`.
- Custom type validators run during record validation. Python's do not.
- Options instead of registration methods; no freeze step.
- Numbers are JavaScript numbers. `Int` versus `Float` is decided by how a literal is written and, for records, by `Number.isInteger`.

## Layout

```
src/            the package; one module per concern, mirrors the Go host
test/           vitest; conformance.test.ts reads ../spec/conformance directly
dist/           build output, not committed
```

## Develop

Node 18 or newer and pnpm.

```bash
cd typescript
pnpm install
pnpm typecheck && pnpm build && pnpm test
```

Or `just test-ts` from the repository root.
