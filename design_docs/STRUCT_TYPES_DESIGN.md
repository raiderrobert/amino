# Amino Struct-as-Type Support Design

## Summary

This document outlines the design for extending amino's struct system to support using structs as first-class types in field definitions, function parameters, and validation contexts.

## Research Foundation

Based on analysis of 10+ DSL languages (GraphQL, Protocol Buffers, Terraform HCL, JSON Schema, TypeScript, Rust, Go, OpenAPI, Avro, Thrift), the following patterns emerged:

### Common Approaches
- **Definition Keywords**: `struct`, `type`, `record`, `message`, `interface`
- **Reference Patterns**: Direct name references (`user: User`) vs path references (`$ref: "#/defs/User"`)
- **Composition**: Embedding, inheritance, union types, intersections
- **Optionality**: Optional field support (see separate optional types design document)

### Best Practices Identified
1. **Clear separation** between definition and usage
2. **Simple, direct references** preferred over complex path syntax
3. **PascalCase naming** for type names is most common
4. **Validation constraints** at the schema level
5. **Support for nested/composed types**

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

### 4. Constraint Propagation

Struct-level constraints and validations:

```amino
struct Email {
    address: Str,
    verified: Bool,
    domain: Str
}

struct User {
    id: Str {min_length: 1, max_length: 50},
    email: Email,
    age: Int {min: 0, max: 150}
} {
    # Struct-level constraints
    constraint: age >= 13 or email.verified == true,
    unique_fields: [id, email.address]
}
```

## Implementation Strategy

### Phase 1: Basic Struct References (MVP)

**Goals:**
- Allow struct names as types in field definitions
- Support struct parameters in functions  
- Basic validation of struct-typed fields

**Changes Required:**
1. **Parser Changes (`amino/schema/parser.py`)**
   - Update `_parse_type_expression()` to recognize struct names
   - Add struct name validation during parsing
   - Handle struct references in function parameters

2. **AST Changes (`amino/schema/ast.py`)**
   - Add `struct_reference` type to field definitions
   - Update `FieldDefinition` to track referenced struct names
   - Extend function parameter types

3. **Type System (`amino/schema/types.py`)**
   - Add `SchemaType.struct_ref` enum value
   - Update `parse_type()` to handle struct references
   - Add struct name resolution logic

4. **Validation (`amino/types/validation.py`)**
   - Extend `TypeValidator` to validate struct-typed fields
   - Add struct instance validation logic
   - Handle nested validation

**Syntax:**
```amino
struct User {
    name: Str,
    age: Int
}

# Basic usage
current_user: User
admin: User

validate_user: (user: User) -> Bool
```

### Phase 2: Nested Structs and Lists

**Goals:**
- Support `List[StructType]`
- Enable nested struct definitions
- Add struct composition

**New Features:**
```amino
struct Address {
    street: Str,
    city: Str  
}

struct User {
    name: Str,
    address: Address,
    previous_addresses: List[Address]
}
```

### Phase 3: Advanced Features

**Goals:**
- Union types (`A | B`)
- Generic structs (`Container[T]`)
- Inheritance (`extends` keyword)
- Struct-level constraints

### Phase 4: Developer Experience

**Goals:**
- Better error messages for struct validation failures
- Schema introspection and documentation generation
- IDE support and auto-completion
- Migration tools for existing schemas

## Grammar Changes (ABNF)

### Current Grammar
```abnf
field-type = primitive-type / custom-type
primitive-type = "Int" / "Str" / "Float" / "Bool"  
custom-type = WORD
```

### Proposed Grammar (Phase 1)
```abnf
field-type = primitive-type / list-type / struct-type / custom-type
primitive-type = "Int" / "Str" / "Float" / "Bool"
list-type = ("List" / "list") "[" field-type "]"
struct-type = struct-name
struct-name = WORD  ; Must reference a defined struct
custom-type = WORD
```

### Extended Grammar (Phase 3)
```abnf
field-type = primitive-type / list-type / struct-type / union-type / generic-type / custom-type
union-type = field-type "|" field-type
generic-type = generic-name "[" type-args "]"
type-args = field-type *("," field-type)
generic-name = WORD
```

## Data Structures

### Extended AST Nodes

```python
@dataclasses.dataclass
class StructReference:
    """Reference to a struct type."""
    struct_name: str
    generic_args: list[str] = dataclasses.field(default_factory=list)

@dataclasses.dataclass  
class UnionType:
    """Union of multiple types."""
    types: list[Union[SchemaType, StructReference]]

@dataclasses.dataclass
class FieldDefinition:
    name: str
    field_type: Union[SchemaType, StructReference, UnionType]
    type_name: str
    element_types: list[str] = dataclasses.field(default_factory=list)
    constraints: dict[str, Any] = dataclasses.field(default_factory=list)
    struct_ref: StructReference | None = None  # New field
```

### Validation Context

```python
@dataclasses.dataclass
class ValidationContext:
    """Context for struct validation."""
    schema_ast: SchemaAST
    struct_definitions: dict[str, StructDefinition]
    validation_path: list[str] = dataclasses.field(default_factory=list)
    circular_refs: set[str] = dataclasses.field(default_factory=set)
```

## Examples

### E-commerce Schema
```amino
struct Money {
    amount: Float {min: 0},
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
    quantity: Int {min: 1},
    unit_price: Money
}

struct Order {
    id: Str,
    customer: Customer,
    items: List[OrderItem],
    total: Money,
    status: Str {enum: [pending, confirmed, shipped, delivered, cancelled]}
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
    username: Str {min_length: 3},
    email: Str,
    role: Str {enum: [admin, editor, author, viewer]}
}

struct Tag {
    id: Str,
    name: Str,
    color: Str
}

struct Article {
    id: Str,
    title: Str {max_length: 200},
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
    content: Str {max_length: 1000},
    created_at: Str
}

# Content validation functions
can_publish_article: (user: User, article: Article) -> Bool
moderate_comment: (comment: Comment, moderator: User) -> Bool
```

## Migration Strategy

### Backward Compatibility
- All existing schemas continue to work unchanged
- Struct definitions remain optional
- No breaking changes to current syntax

### Migration Path
1. **Identify Patterns**: Find repeated field patterns in existing schemas
2. **Extract Structs**: Create struct definitions for common patterns  
3. **Update References**: Replace repeated patterns with struct references
4. **Add Validation**: Enhance with struct-level constraints

### Example Migration
```amino
# Before (repeated pattern)
user_name: Str
user_email: Str
user_active: Bool

admin_name: Str  
admin_email: Str
admin_active: Bool

# After (with struct)
struct User {
    name: Str,
    email: Str,
    active: Bool
}

user: User
admin: User
```

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

## Risks and Considerations

### Complexity
- **Learning Curve**: More concepts for users to understand
- **Implementation Complexity**: More code to maintain and test
- **Performance**: Validation overhead for nested structures

### Migration Challenges  
- **Breaking Changes**: Future advanced features might require changes
- **Tooling Updates**: All tools need to support new features
- **Documentation**: Need comprehensive examples and guides

### Design Decisions
- **Syntax Choices**: Balance familiarity vs expressiveness
- **Feature Scope**: How much to implement in each phase
- **Performance vs Features**: Trade-offs in validation complexity

## Success Metrics

### Adoption Metrics
- Percentage of schemas using struct types
- Reduction in schema line count due to DRY
- Number of struct definitions created

### Quality Metrics
- Improved validation accuracy
- Reduced validation errors due to better structure
- Developer satisfaction surveys

### Technical Metrics
- Performance impact of struct validation
- Memory usage of complex schemas
- Test coverage of new features

## Conclusion

Adding struct-as-type support to amino will significantly enhance its expressiveness while maintaining simplicity. The phased approach allows for gradual implementation and testing, ensuring stability and backward compatibility.

The design draws from proven patterns in other DSL languages while staying true to amino's philosophy of clarity and ease of use. This enhancement positions amino as a more powerful tool for complex validation and schema definition scenarios.