# ADR 004: Schema Language Features

**Date**: 2026-02-19
**Status**: Accepted

## Context

The core schema language (fields, structs, functions) needs to support three additional capabilities identified in earlier design work: field-level constraints for validation, optional fields for real-world incomplete data, and struct-as-type references for composable data modeling. These are schema language features that affect the parser, AST, and decision validator but not the rule expression grammar.

## Decisions

### 1. Field-level constraints use block syntax

Fields can declare validation constraints inline using a block syntax after the type:

```
age: Int {min: 18, max: 120}
username: Str {minLength: 3, maxLength: 20, pattern: "^[a-zA-Z0-9_]+$"}
status: Str {oneOf: ["active", "inactive", "pending"]}
tags: List[Str] {minItems: 1, maxItems: 10, unique: true}
price: Float {min: 0.01}
```

Supported constraint keys by base type:

| Base type | Constraints |
|-----------|------------|
| `Int`, `Float` | `min`, `max`, `exclusiveMin`, `exclusiveMax` |
| `Str` | `minLength`, `maxLength`, `exactLength`, `pattern`, `format`, `oneOf` |
| `List[T]` | `minItems`, `maxItems`, `exactItems`, `unique` |
| Any | `oneOf`, `const` |

Multiple constraints within a block are combined with AND logic — all must be satisfied.

**Constraint syntax** chosen over alternatives (inline `(min=18)`, annotation `@min(18)`) because block syntax cleanly separates type from constraints and scales to multiple constraints without becoming unreadable.

**Constraints are enforced by the DecisionValidator**, not the rule compiler. A constraint violation on incoming data is a validation failure, not a type error.

**Rationale**: Constraints reduce the need for boilerplate validation rules. `status: Str {oneOf: ["active", "inactive"]}` is clearer and more maintainable than a rule that checks every possible invalid status value. The `oneOf` constraint in particular reduces the need for custom types in enumeration cases.

### 2. Optional fields use `?` suffix syntax

Fields are required by default. Optional fields use `?` after the type:

```
# Top-level optional fields
email: Str?
phone: Str?
age: Int?

# Optional structs
struct UserProfile {
    id: Str,           # required
    name: Str,         # required
    bio: Str?,         # optional
    avatar_url: Str?   # optional
}

# Optional collections
tags: List[Str]?       # the list itself is optional
scores: List[Int?]     # required list with optional elements
notes: List[Str?]?     # optional list with optional elements
```

**Null and missing are treated as equivalent** for optional fields. A decision that omits an optional field and one that includes it with a `null` value are both valid.

**Optional fields with constraints** — constraints apply only when the field is present and non-null:
```
age: Int? {min: 13, max: 120}   # if present, must be 13-120
```

**Validation behavior**:
- Required field missing in `strict` decisions_mode: rejection
- Required field missing in `loose` decisions_mode: skip-and-warn (per ADR 001)
- Optional field missing: always valid, no warning

**Rationale**: Real-world data is rarely complete. IoT sensors miss readings. API responses omit fields. Optional support prevents spurious validation failures and removes the need for upstream data cleaning before evaluation.

### 3. Structs are first-class types

Structs defined in the schema can be used as field types and function parameter/return types anywhere a primitive type is valid:

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

# Struct in function signature
validate_address: (addr: Address) -> Bool
```

**Nested and recursive structs** are supported to arbitrary depth. The schema validator checks for circular references and rejects them.

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

**Struct references in rules** use dot notation, consistent with the current behavior:
```
customer.billing_address.city = 'San Francisco'
```

**Deferred features** — the following were identified in design exploration but are deferred as they add significant complexity without clear near-term use cases:
- Generic/parameterized structs (`struct Container[T]`)
- Struct inheritance (`struct User extends BaseEntity`)
- Union struct types (`customer: IndividualCustomer | BusinessCustomer`)

**Rationale**: Struct-as-type is foundational for real-world data modeling. Repeating fields across multiple structs violates DRY and makes schemas harder to maintain. Nested structs also enable richer rule expressions via dot notation without additional rule syntax.

## Consequences

- The schema parser must handle constraint blocks `{...}`, the `?` suffix, and struct type references in `type_expr`.
- The schema AST gains `optional: bool` and `constraints: dict` on `FieldDefinition`.
- The schema validator must resolve struct type references (ensuring referenced structs are defined) and detect circular struct references.
- The DecisionValidator enforces constraints at evaluation time, not the compiler.
- The `SchemaRegistry` must support struct field traversal for nested dot-notation access in rules.
- The grammar's `type_expr <- list_type / primitive / identifier` already handles struct references via `identifier`; validation of whether `identifier` names a known struct or custom type happens in the schema validator post-parse.

## Open Questions

- Should `format` in string constraints (e.g., `{format: "email"}`) resolve to a built-in validator, or must users also call `register_type`? Suggestion: `format` names map to built-in validators where available; custom formats require `register_type`.
- Cross-field constraints (e.g., `end_date` must be after `start_date`) are out of scope for now but worth tracking as a future ADR.
