# Amino Optional Types Design

## Summary

This document outlines the design for adding optional field support to amino using the `?` syntax marker. Optional fields allow schema authors to specify that certain fields may be absent or null, providing flexibility in data validation while maintaining type safety.

## Research Foundation

Based on analysis of modern DSL and schema languages, optional field patterns are nearly universal:

### Common Approaches
- **TypeScript/JavaScript**: `field?: Type`
- **Rust**: `Option<T>` or `field: Type | undefined`
- **Swift**: `var field: Type?`
- **Kotlin**: `field: Type?`
- **C#**: `Type? field`
- **GraphQL**: `field: Type` (optional by default) vs `field: Type!` (required)
- **JSON Schema**: `"required": ["field1", "field2"]` array
- **Protocol Buffers**: `optional` keyword

### Best Practices Identified
1. **Clear visual distinction** between required and optional fields
2. **Simple, consistent syntax** across all field types
3. **Support for optional collections** and complex types
4. **Null vs undefined semantics** handling
5. **Backward compatibility** with existing schemas

## Current Amino State

### What Works Today
```amino
# Only required fields are supported
name: Str
age: Int
active: Bool

# Struct definitions
struct User {
    name: Str,
    email: Str,
    age: Int
}
```

### Current Limitations
- **No optional fields**: All fields are required by default
- **No null handling**: Cannot represent missing or null values
- **Rigid validation**: Schemas must match exactly
- **Poor API flexibility**: Cannot handle partial data updates

## Proposed Design

### 1. Basic Optional Field Syntax

Use the `?` suffix to mark fields as optional:

```amino
# Optional primitive types
name: Str?
age: Int?
active: Bool?
email: Str?

# Required fields (unchanged)
id: Str
created_at: Str
```

### 2. Optional Fields in Structs

```amino
struct User {
    id: Str,              # Required
    name: Str,            # Required
    email: Str?,          # Optional
    phone: Str?,          # Optional
    age: Int?,            # Optional
    is_admin: Bool        # Required
}
```

### 3. Optional Collections

```amino
# Optional lists
tags: List[Str]?          # List itself is optional
categories: List[Str?]?   # Optional list of optional strings

# Required list with optional elements
scores: List[Int?]        # Required list, but elements can be null
```

### 4. Optional Function Parameters and Return Types

```amino
# Optional parameters
find_user: (id: Str, include_deleted: Bool?) -> User?

# Optional return types
get_user_by_email: (email: Str) -> User?
update_user: (id: Str, data: User) -> Bool?
```

## Design Alternatives

### Optional Field Syntax Options

**Suffix syntax (chosen):**
```amino
name: Str?
age: Int?
```

**Prefix syntax (alternative):**
```amino
name: ?Str
age: ?Int
```

**Wrapper type syntax (alternative):**
```amino
name: Optional[Str]
age: Optional[Int]
```

**Rationale**: Suffix syntax is familiar from TypeScript, Swift, Kotlin and visually lightweight.

### Null vs Missing Semantics

**Treat null and missing as equivalent (chosen):**
- Both `null` and absent fields are valid for optional types
- Simpler mental model for developers

**Distinguish null from missing (alternative):**
- `field?: Type` allows missing or null
- `field: Type | null` allows null but field must be present
- More precise but adds complexity

**Rationale**: Equivalent treatment covers most use cases with simpler semantics.

### Optional Collection Elements

**Element-level optionality:**
```amino
scores: List[Int?]  # List of optional integers
```

**Collection-level optionality:**
```amino
scores: List[Int]?  # Optional list of integers
```

**Both (chosen):**
```amino
scores: List[Int?]?  # Optional list of optional integers
```

**Rationale**: Maximum flexibility for complex data structures.

## Grammar Impact

**Current field syntax:**
```abnf
field-definition = identifier ":" SP type [field-constraints] [comment]
```

**Extended field syntax:**
```abnf
field-definition = identifier ":" SP type [field-optional] [field-constraints] [comment]
field-optional = "?"
```

## Validation Semantics

**Missing vs Null Values:**
- Missing field: Key absent from data object
- Null field: Key present with `null` value
- Both are valid for optional fields

**Validation Rules:**
- Required fields: Must be present and non-null
- Optional fields: Can be missing or null
- Optional with constraints: If present and non-null, must satisfy constraints

## Implementation Impact

This feature will require changes to:
- Parser: Recognize `?` suffix and track optional flag
- Validation Engine: Allow missing/null values for optional fields
- AST: Extend field definitions to include optional metadata
- Error Reporting: Distinguish required vs optional field violations

## Examples

### User Profile Schema
```amino
struct UserProfile {
    # Required fields
    id: Str,
    username: Str,
    email: Str,
    
    # Optional fields
    first_name: Str?,
    last_name: Str?,
    phone: Str?,
    bio: Str?,
    avatar_url: Str?,
    birth_date: Str?,
    
    # Optional with constraints
    age: Int? {min: 13, max: 120}
}
```

### API Response Schema
```amino
struct ApiResponse {
    # Always present
    success: Bool,
    timestamp: Str,
    
    # Optional depending on success
    data: Str?,
    error_message: Str?,
    error_code: Int?
}

# Function with optional parameters
handle_request: (path: Str, method: Str, headers: List[Str]?) -> ApiResponse
```

## Benefits

### For Schema Authors
- **Flexible Schemas**: Model real-world data where some fields may be missing
- **Evolutionary Design**: Add new optional fields without breaking existing data
- **Clear Intent**: Explicitly express which fields are essential vs nice-to-have
- **API Design**: Better support for PATCH operations and partial updates

### For Data Validation  
- **Realistic Validation**: Handle incomplete data gracefully
- **Better Error Messages**: Distinguish between missing required vs optional fields
- **Partial Validation**: Validate only the fields that are present
- **Null Safety**: Explicit handling of null values

## Backward Compatibility

All existing schemas continue to work unchanged:
- No breaking changes to current required field syntax
- Optional syntax is purely additive
- Validation behavior unchanged for existing schemas

## Trade-offs and Considerations

### Simplicity vs Precision
- **Pro**: Simple `?` syntax is easy to understand and use
- **Con**: Doesn't distinguish between null and missing values
- **Decision**: Simplicity wins for most use cases, precision can be added later if needed

### Type System Complexity
- **Pro**: Optional types are foundational for realistic data modeling
- **Con**: Adds another dimension to the type system
- **Decision**: Essential feature that justifies the complexity

### Validation Performance
- **Pro**: Clearer validation semantics for incomplete data
- **Con**: Additional checks for optional field handling
- **Decision**: Minimal performance impact for significant usability gain

## Conclusion

Optional field support is foundational for real-world data validation. The `?` syntax follows familiar patterns from modern typed languages while maintaining amino's simplicity and clarity.