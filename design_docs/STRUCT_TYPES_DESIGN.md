# Amino Struct-as-Type Support Design

## Summary

This document outlines the design for extending amino's struct system to support using structs as first-class types in field definitions, function parameters, and validation contexts.

## Research Foundation

Based on analysis of 10+ DSL languages (GraphQL, Protocol Buffers, Terraform HCL, JSON Schema, TypeScript, Rust, Go, OpenAPI, Avro, Thrift), the following patterns emerged:

### Common Approaches
- **Definition Keywords**: `struct`, `type`, `record`, `message`, `interface`
- **Reference Patterns**: Direct name references (`user: User`) vs path references (`$ref: "#/defs/User"`)
- **Composition**: Embedding, inheritance, union types, intersections

### Best Practices Identified
1. **Clear separation** between definition and usage
2. **Simple, direct references** preferred over complex path syntax
3. **PascalCase naming** for type names is most common
4. **Support for nested/composed types**

## Current Amino State

### What Works Today
```amino
# Struct definitions
struct User {
    name: Str,
    email: Str,
    age: Int
}

# Field definitions  
name: Str
age: Int
active: Bool

# Function definitions
validate_user: (name: Str, age: Int) -> Bool
```

### Current Limitations
- Structs cannot be used as types in fields
- No way to reference structs in function parameters
- No composition or nesting capabilities
- Validation only works on primitive types

## Proposed Design

**Note**: This design focuses on struct-as-type functionality. For optional field support (`field: Type?`), see the separate `optional_types_design.md` document.

### 1. Basic Struct-as-Type Support

Allow structs to be referenced by name as types:

```amino
struct User {
    id: Str,
    name: Str,
    email: Str,
    age: Int
}

struct Company {
    name: Str,
    domain: Str,
    active: Bool
}

# Use structs as field types
user: User
company: Company
admin: User

# Use in functions
create_user: (data: User) -> Bool
get_company: (id: Str) -> Company
```

### 2. Nested Struct Support

Enable struct composition and nesting:

```amino
struct Address {
    street: Str,
    city: Str,
    country: Str
}

struct User {
    id: Str,
    name: Str,
    email: Str,
    address: Address,
    secondary_addresses: List[Address]
}

# Multi-level nesting
struct Department {
    name: Str,
    manager: User,
    employees: List[User]
}

struct Company {
    name: Str,
    headquarters: Address,
    departments: List[Department]
}
```

### 3. Advanced Type Features

#### Union Types
```amino
struct IndividualCustomer {
    first_name: Str,
    last_name: Str,
    ssn: Str
}

struct BusinessCustomer {
    company_name: Str,
    tax_id: Str,
    industry: Str
}

# Union type syntax
customer: IndividualCustomer | BusinessCustomer
```

#### Generic/Parameterized Structs
```amino
struct ApiResponse[T] {
    success: Bool,
    data: T,
    error: Str
}

struct PaginatedList[T] {
    items: List[T],
    total_count: Int,
    page: Int,
    page_size: Int
}

# Usage
user_response: ApiResponse[User]
user_list: PaginatedList[User]
```

#### Struct Inheritance/Extension
```amino
struct BaseEntity {
    id: Str,
    created_at: Str,
    updated_at: Str
}

struct User extends BaseEntity {
    name: Str,
    email: Str
}

struct Company extends BaseEntity {
    name: Str,
    domain: Str
}
```

## Design Alternatives

### Reference Syntax Options

**Direct name references (chosen):**
```amino
user: User
```

**Path-based references (alternative):**
```amino
user: $ref("#/structs/User")
```

**Rationale**: Direct references are simpler and more familiar to developers from other typed languages.

### Union Type Syntax Options

**Pipe syntax (chosen):**
```amino
customer: IndividualCustomer | BusinessCustomer
```

**Enum-style (alternative):**
```amino
customer: Union[IndividualCustomer, BusinessCustomer]
```

**Rationale**: Pipe syntax is more concise and widely adopted across modern languages.

### Generic/Parameterized Struct Options

**Angle bracket syntax (chosen):**
```amino
struct Container[T] {
    item: T
}
```

**Function-style (alternative):**
```amino
struct Container(T) {
    item: T
}
```

**Rationale**: Angle brackets clearly distinguish type parameters from value parameters.

### Inheritance vs Composition

**Inheritance approach:**
```amino
struct User extends BaseEntity {
    name: Str
}
```

**Composition approach:**
```amino
struct User {
    base: BaseEntity,
    name: Str
}
```

**Mixed approach (chosen):** Support both patterns, with inheritance for "is-a" relationships and composition for "has-a" relationships.

## Grammar Changes (ABNF)

### Current Grammar
```abnf
field-type = primitive-type / custom-type
primitive-type = "Int" / "Str" / "Float" / "Bool"  
custom-type = WORD
```

### Extended Grammar
```abnf
field-type = primitive-type / list-type / struct-type / union-type / generic-type / custom-type
primitive-type = "Int" / "Str" / "Float" / "Bool"
list-type = "List" "[" field-type "]"
struct-type = struct-name
struct-name = WORD  ; Must reference a defined struct
union-type = field-type "|" field-type
generic-type = generic-name "[" type-args "]"
type-args = field-type *("," field-type)
generic-name = WORD
custom-type = WORD
```

## Implementation Impact

This feature will require changes to:
- Parser: Recognize struct names as valid type expressions
- AST: Extend type system to include struct references
- Type System: Add struct reference validation and resolution
- Validation Engine: Handle nested struct validation

## Examples

### E-commerce Schema
```amino
struct Money {
    amount: Float,
    currency: Str
}

struct Address {
    street: Str,
    city: Str,
    state: Str,
    zip_code: Str,
    country: Str
}

struct Customer {
    id: Str,
    email: Str,
    name: Str,
    billing_address: Address,
    shipping_address: Address
}

struct Product {
    id: Str,
    name: Str,
    price: Money,
    category: Str,
    in_stock: Bool
}

struct OrderItem {
    product: Product,
    quantity: Int,
    unit_price: Money
}

struct Order {
    id: Str,
    customer: Customer,
    items: List[OrderItem],
    total: Money,
    status: Str
}

# Functions using struct types
calculate_order_total: (items: List[OrderItem]) -> Money
validate_shipping_address: (address: Address) -> Bool
process_order: (order: Order) -> Bool
```

### Content Management System
```amino
struct User {
    id: Str,
    username: Str,
    email: Str,
    role: Str
}

struct Tag {
    id: Str,
    name: Str,
    color: Str
}

struct Article {
    id: Str,
    title: Str,
    content: Str,
    author: User,
    tags: List[Tag],
    published: Bool,
    published_at: Str
}

struct Comment {
    id: Str,
    article: Article,
    author: User,
    content: Str,
    created_at: Str
}

# Content validation functions
can_publish_article: (user: User, article: Article) -> Bool
moderate_comment: (comment: Comment, moderator: User) -> Bool
```

## Backward Compatibility

All existing schemas continue to work unchanged:
- Struct definitions remain optional
- No breaking changes to current syntax
- Primitive types and current features unaffected

## Benefits

### For Schema Authors
- **DRY Principle**: Eliminate repeated field definitions
- **Better Organization**: Logical grouping of related fields
- **Easier Maintenance**: Change struct once, update everywhere
- **Clear Semantics**: Express intent more clearly

### For Validators
- **Structured Validation**: Validate complex nested data
- **Better Error Messages**: Precise error locations in nested structures
- **Reusable Logic**: Validate struct types consistently

### For Tooling
- **Schema Documentation**: Generate better documentation
- **Code Generation**: Generate strongly-typed code
- **IDE Support**: Auto-completion and validation
- **Testing**: Generate test data structures

## Trade-offs and Considerations

### Complexity vs Expressiveness
- **Pro**: Eliminates code duplication, clearer data modeling
- **Con**: Additional concepts for users to learn
- **Decision**: Benefits outweigh learning curve for non-trivial schemas

### Performance vs Features
- **Pro**: Better structured validation, clearer error messages
- **Con**: Additional validation overhead for nested structures
- **Decision**: Performance impact acceptable for improved data modeling

### Syntax Familiarity
- **Pro**: Direct references (`user: User`) familiar from typed languages
- **Con**: Differs from JSON Schema's path-based references
- **Decision**: Prioritize developer familiarity over existing schema language consistency

## Conclusion

Adding struct-as-type support enhances amino's expressiveness for complex data modeling while maintaining its core simplicity. The design follows familiar patterns from modern typed languages, prioritizing developer experience and clear syntax over alternative approaches.