# Schema Language Reference

The schema is the contract between a developer and the people who write expressions. It declares every field, type, struct, constraint, and function an expression may reference. Anything not declared cannot be named, which is the foundation of the [security model](security.md).

Schema files use the `.amn` extension by convention and are passed to `amino.load_schema()` as a path or as text. The formal grammar is [spec/grammar/schema.peg](../spec/grammar/schema.peg).

```
# Loan application
amount: Int
state_code: Str
credit_score: Int {min: 300, max: 850}
email: Str?
contact: email
tags: List[Str]

struct Address { street: Str, city: Str, country: Str }
struct Customer { id: Str, billing: Address, shipping: Address? }
customer: Customer

risk_model: (score: Int, amount: Int) -> Float
```

## Fields

One per line, `name: Type`. Comments start with `#`.

## Primitive types

`Int`, `Float`, `Str`, `Bool`. These are the only types a literal in an expression can have, and the only bases a custom type can have.

## Lists

`List[T]`. Used with `in` and `not in` in expressions, and validated for element type and count on the Python target.

```
tags: List[Str]
values: List[Int|Str]      # union element type; unions are valid only inside List[...]
```

## Optional fields

A trailing `?` makes a field optional. Null and missing are equivalent.

```
email: Str?
age: Int? {min: 13}        # constraint applies only when present
```

A required field that is missing from a record is rejected in strict decisions mode, or dropped with a warning in loose mode. See [targets.md](targets.md#decision-validation).

On SQL targets an optional field maps naturally to a nullable column, and comparisons against NULL follow SQL's three-valued logic, which differs from the Python target. See [targets.md](targets.md#divergence-from-the-python-evaluator).

## Constraints

A block after the type. All constraints in a block must hold. They are enforced when the Python target validates a record, not when an expression is parsed, and SQL targets do not enforce them at all; the database's own constraints are the equivalent there.

```
age: Int {min: 18, max: 120}
username: Str {minLength: 3, maxLength: 20, pattern: "^[a-zA-Z0-9_]+$"}
status: Str {oneOf: ["active", "inactive", "pending"]}
tags: List[Str] {minItems: 1, maxItems: 10, unique: true}
```

Implemented constraint keys:

| Key | Applies to | Meaning |
|---|---|---|
| `min`, `max` | `Int`, `Float` | inclusive bounds |
| `exclusiveMin`, `exclusiveMax` | `Int`, `Float` | exclusive bounds |
| `minLength`, `maxLength`, `exactLength` | `Str` | character count |
| `pattern` | `Str` | regex the whole value must match |
| `oneOf` | any | value is one of the listed literals |
| `const` | any | value equals this literal |
| `minItems`, `maxItems` | `List` | element count |
| `unique` | `List` | elements are distinct |

The schema parser accepts any key, so `format` and `exactItems` parse but are not enforced. They appeared in earlier design documents and are not implemented. Cross-field constraints, such as `end_date` after `start_date`, are out of scope; write them as expressions.

## Structs

A struct is a named group of fields usable as a type anywhere a primitive is. Fields may be separated by commas or newlines. Nesting is unlimited; cycles are rejected by the schema validator.

```
struct OrderItem {
    product_id: Str,
    quantity: Int
}

struct Order {
    items: List[OrderItem],
    total: Float,
    shipping: Address?
}
```

Expressions reach into structs with dot notation: `order.shipping.city = 'Austin'`. SQL targets need a column mapping for every dotted path they will see; see [targets.md](targets.md#column-mapping).

## Functions

`name: (params) -> ReturnType`. Parameters and return types use field type syntax including `?`. The implementation is supplied in Python with `funcs=` on `load_schema()` or `add_function()`.

```
risk_model: (score: Int, amount: Int) -> Float
find_user: (id: Str, include_deleted: Bool?) -> User?
```

A declared function is the only way expression text can cause code to run. The developer decides what to declare. On SQL targets the function is emitted by name and must exist in the database with a compatible signature.

## Custom types

A custom type is a name, a base primitive, and a validator. Register it before the first parse. The name is then valid as a field type.

```python
engine.register_type("ipv4", base="Str", validator=is_valid_ipv4)
```

```
source_ip: ipv4
```

Built in: `ipv4`, `ipv6`, `cidr`, `email`, `uuid`, all with base `Str`. The validator runs during record validation on the Python target. The base type is what SQL targets use to choose a parameter type, and what operators fall back to when no overload is registered for the custom type itself.

## Type enforcement modes

`decisions_mode` on `load_schema()` controls what the Python target does with a non-conforming record: `"strict"` raises `DecisionValidationError`; `"loose"` (default) drops the offending fields, records a warning on the result, and evaluates on the rest. Values are never coerced.

`rules_mode` was designed to control what happens when an expression has a type mismatch. It is accepted and currently has no effect, because mismatches on built-in operators are not detected. See [expression-language.md](expression-language.md#type-checking).

## Export

`engine.export_schema()` returns the schema as `.amn` text, with structs first, then fields, then functions. A JSON form including operator signatures is planned so that a client-side validator can be built from it.
