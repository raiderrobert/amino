# Schema Language Reference

## Overview

The amino schema language defines the type system for an engine instance: the fields, their types and constraints, struct definitions, and function signatures. The schema is the stable anchor that rules are compiled against and decisions are validated against.

Schema files use the `.amn` extension. The schema is passed to `amino.load_schema()` either as a file path or as a raw string.

## Field definitions

Fields are declared with the syntax `name: Type`. Each field occupies one line.

```
age: Int
username: Str
score: Float
active: Bool
```

## Primitive types

| Name | Python equivalent | Notes |
|------|-------------------|-------|
| `Int` | `int` | |
| `Float` | `float` | |
| `Str` | `str` | |
| `Bool` | `bool` | |

## Complex types

**Lists** are declared with `List[T]`:

```
tags: List[Str]
scores: List[Float]
```

**Union-typed lists** allow multiple element types:

```
values: List[Int|Str|Bool]
```

Union types are only valid inside `List[...]`. Top-level union field types are not supported.

**Struct references** use the struct name as the type. See the Structs section below.

## Optional fields

Fields are required by default. Append `?` after the type to mark a field as optional:

```
email: Str?
phone: Str?
age: Int?
```

Null and missing are treated as equivalent for optional fields. A decision that omits an optional field and one that includes it with a `null` value are both valid.

Optional fields with constraints — constraints apply only when the field is present and non-null:

```
age: Int? {min: 13, max: 120}   # if present, must be 13-120
```

**Validation behavior:**

- Required field missing in `strict` decisions mode: rejected with `DecisionValidationError`
- Required field missing in `loose` decisions mode: field is skipped and a warning is added to `MatchResult.warnings`
- Optional field missing: always valid, no warning

## Constraints

Fields can declare validation constraints inline using block syntax after the type:

```
age: Int {min: 18, max: 120}
username: Str {minLength: 3, maxLength: 20, pattern: "^[a-zA-Z0-9_]+$"}
status: Str {oneOf: ["active", "inactive", "pending"]}
tags: List[Str] {minItems: 1, maxItems: 10, unique: true}
price: Float {min: 0.01}
```

Multiple constraints within a block are combined with AND logic — all must be satisfied.

**Supported constraint keys:**

| Constraint | Applicable types | Meaning |
|------------|-----------------|---------|
| `min` / `max` | `Int`, `Float` | Inclusive numeric bounds |
| `exclusiveMin` / `exclusiveMax` | `Int`, `Float` | Exclusive numeric bounds |
| `minLength` / `maxLength` / `exactLength` | `Str` | Character count bounds |
| `pattern` | `Str` | Regex pattern the value must match |
| `format` | `Str` | Named format validator (email, url, uuid, etc.) |
| `oneOf` | Any | Value must be one of the listed literals |
| `const` | Any | Value must equal exactly this literal |
| `minItems` / `maxItems` / `exactItems` | `List` | Element count bounds |
| `unique` | `List` | All elements must be distinct |

Constraints are enforced by the `DecisionValidator` at evaluation time, not by the rule compiler. A constraint violation on incoming data is a validation failure, not a type error.

**Deferred / future — cross-field validation:** Constraints that reference another field's value (e.g., requiring `end_date` to be after `start_date`) are out of scope for the current constraint system. Each constraint block is evaluated against its own field in isolation. Cross-field validation is identified as a future extension point.

## Structs

Structs are first-class types. A struct defined in the schema can be used as a field type anywhere a primitive type is valid.

```
struct Address {
    street: Str,
    city: Str,
    country: Str
}

struct Customer {
    id: Str,
    name: Str,
    billing_address: Address,    # struct as field type
    shipping_address: Address?   # optional struct
}
```

Struct fields can be separated by commas or newlines; mixing within one struct is permitted.

**Nested structs** are supported to arbitrary depth. The schema validator checks for circular references and rejects them.

**List of structs** is valid:

```
struct OrderItem {
    product_id: Str,
    quantity: Int
}

struct Order {
    items: List[OrderItem],
    total: Float
}
```

**Struct references in rules** use dot notation:

```
customer.billing_address.city = 'San Francisco'
```

## Function declarations

Functions are declared with the syntax `name: (params) -> ReturnType`. Function declarations appear in the schema alongside field definitions.

```
validate_address: (addr: Address) -> Bool
score_customer: (id: Str, tier: Str) -> Float
```

Parameters use the same type syntax as fields, including the `?` optional suffix, and return types can also be marked optional with `?`. Function implementations are registered at engine construction time via `engine.add_function()`.

```
find_user:        (id: Str, include_deleted: Bool?) -> User    # optional parameter
get_user_by_email: (email: Str) -> User?                       # optional return type
find_user:        (id: Str, include_deleted: Bool?) -> User?   # both
```

## Custom types

Custom types are registered at engine construction time via `engine.register_type()`. Once registered, the type name is valid in schema definitions.

```python
engine.register_type('ipv4', base='Str', validator=is_valid_ipv4)
engine.register_type('cidr', base='Str', validator=is_valid_cidr)
```

After registration, the type name can be used in the schema:

```
source_ip: ipv4
network: cidr
```

The base type (`Str`, `Int`, `Float`, or `Bool`) governs default operator behavior when no type-specific operator is registered. The validator function runs during decision validation (`fn(value) -> bool | ValidationResult`).

Custom type registrations must complete before the first `compile()` or `eval()` call.

## Type enforcement modes

Type enforcement is configured independently for rules and decisions at engine construction:

- **`strict` rules mode** — type mismatch in a rule expression raises `TypeMismatchError` at `compile()` time
- **`loose` rules mode** — type mismatch logs a warning; the rule is compiled with best-effort type information
- **`strict` decisions mode** — non-conforming decision data raises `DecisionValidationError`
- **`loose` decisions mode** — non-conforming fields are skipped; a warning is added to `MatchResult.warnings`

Loose mode is skip-and-warn. Type coercion (e.g., `"600"` → `600`) is explicitly not performed — types are never silently changed.

## Grammar

See [docs/grammar/schema.peg](grammar/schema.peg) for the formal PEG grammar.
