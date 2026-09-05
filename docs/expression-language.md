# Expression Language Reference

An amino expression is a single, side-effect-free condition over one record, written against a schema. It is the language under features like rules engines and query boxes, so it is one fixed grammar: a developer supplies vocabulary through the schema (fields, types, functions, custom operators) but not syntax. A fixed grammar is what lets features share the language, lets it be implemented in more than one host, and lets it be safe to accept from untrusted users. See [ADR 005](adr/005-one-language-for-user-written-conditions.md).

The same expression can be evaluated in-process or compiled to SQL. Which happens is a property of the target, not the expression. See [targets.md](targets.md).

```
credit_score < 600 and state_code in ['CA', 'NY']
customer.billing_address.city = 'Austin'
toxicity_score(content.text) > 0.9 or not moderated
```

## Atoms

**Field references** resolve against the schema. Dot notation traverses struct fields. An identifier that is not in the schema is a parse error.

```
age
customer.billing_address.city
```

**Literals** come in five kinds. There is no escape mechanism in strings, so a string literal cannot contain a single quote. This is a known limitation tracked in ADR 005.

```
'San Francisco'     # Str, single-quoted
600                 # Int
600.0               # Float, tried before Int
true / false        # Bool
['a', 'b', 'c']     # List, literals only, used on the right of in / not in
```

**Function calls** are `identifier(` followed by comma-separated expressions and `)`. Arguments are full expressions. The function must be declared in the schema; see [Type checking](#type-checking) for the current state of that rule.

```
validate_address(customer.billing_address)
score_customer(id, tier)
```

**Parentheses** group explicitly.

```
(age >= 18 and age <= 65) or vip
```

## Operators

The parser is a Pratt parser. Every operator has a binding power (higher binds tighter), an associativity, and a type signature. Built-in operators and their binding powers:

| Operator | Kind | Binding power | Signature |
|---|---|---|---|
| `or` | infix | 10 | `(Bool, Bool) -> Bool` |
| `and` | infix | 20 | `(Bool, Bool) -> Bool` |
| `not` | prefix | 30 | `(Bool) -> Bool` |
| `in`, `not in` | infix | 40 | `(T, List) -> Bool` |
| `=`, `!=` | infix | 40 | `(T, T) -> Bool` |
| `>`, `<`, `>=`, `<=` | infix | 40 | `(T, T) -> Bool` |
| `contains` | infix | 40 | `(Str, Str) -> Bool` |

All comparison and membership operators share binding power 40 and are left-associative, so `a = b = c` parses as `(a = b) = c`. Write parentheses when in doubt. SQL targets emit parentheses around every binary node so precedence never depends on the database.

`and`, `or`, `not`, parentheses, literals, field references, and function calls are the irreducible minimum. They are present in every operator preset and cannot be removed.

### Operator presets

Chosen at `load_schema()` time with the `operators` argument.

| Preset | Operators |
|---|---|
| `'standard'` (default) | everything in the table above |
| `'minimal'` | `and`, `or`, `not` only |
| a `list[str]` | the named built-ins, plus `and`, `or`, `not` always |

`'minimal'` exists for domains that want an entirely custom operator vocabulary, such as `A precedes B and C precedes D`, while keeping compound rules.

### Keyword operators versus function calls

`identifier(` is always a function call. An identifier in infix position that is not followed by `(` is a keyword operator. `precedes` as an operator and `precedes(a, b)` as a function can coexist.

### Custom operators

Registered before the first `parse()`, `compile()`, or `eval()`. See [api.md](api.md#register_operator) for the full signature.

```python
engine.register_operator(
    keyword="precedes", fn=event_precedes, binding_power=40,
    input_types=("Str", "Str"), return_type="Bool",
)
engine.register_operator(
    symbol="~", kind="prefix", fn=bitwise_not, binding_power=50,
    input_types=("Int",), return_type="Int",
)
```

Exactly one of `symbol` or `keyword`. `kind` is `'infix'` or `'prefix'`. A `'postfix'` kind is accepted by the API but is not implemented; the operator is parsed as infix.

A custom operator has a Python implementation, so only the Python target can execute it. SQL targets raise `UnsupportedExpressionError` when they encounter one. Other host implementations validate it from its signature alone, which is why `input_types` and `return_type` are required.

## Type checking

Parsing resolves every node's type from the schema and annotates the AST. The root's type is the expression's result type: `Bool` for a predicate, `Int` or `Float` for a scoring expression.

What the parser rejects today:

- A field reference not in the schema.
- An operator with no registration for the operand types when more than one registration exists for that token. This is how a domain can give `=` a different implementation for `cidr` operands.

What the parser does **not** reject today, and should:

- A built-in comparison between mismatched types. `name = 5` on a `Str` field parses, and evaluates false on every target. `score contains 'x'` on an `Int` field parses. This is because built-in operators are registered with wildcard signatures, and a single registration is always accepted regardless of operand types.
- A function call to a function not declared in the schema. It is given type `Any`. On the Python target it fails at evaluation. On SQL targets it is emitted verbatim, which is a security defect. See [security.md](security.md#implementation-status).

`rules_mode` on `load_schema()` was designed to switch between raising and warning on type mismatches. It is accepted and currently has no effect, because no mismatch is detected. Both gaps are recorded in [ADR 005](adr/005-one-language-for-user-written-conditions.md) and are scheduled ahead of new features.

## Result types

An expression usually has type `Bool`. Expressions of type `Int` or `Float` are valid and are used by the Python target's `score` match mode, where `Bool` results coerce to `1` and `0`. SQL targets accept only `Bool` roots since they produce a `WHERE` predicate.

## What is deliberately absent

These are not missing features. Leaving them out is what keeps the language small enough to share across features, reimplement in another host, and accept from untrusted users.

- No assignment, variables, or `let`.
- No loops or recursion.
- No user-defined functions inside the language. Functions are declared in the schema and implemented by the developer.
- No string escaping or interpolation.
- No statements. One expression is the whole program.
- No projection, ordering, or aggregation. The expression says which records qualify, not what to return.

## Grammar

The formal grammar of the irreducible minimum is [grammar/rules.peg](grammar/rules.peg). It is the specification that every host implementation must match. Operator-level parsing is driven by the Pratt table and is described by the binding-power table above.
