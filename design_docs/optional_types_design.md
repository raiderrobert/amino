# Amino Optional Types Design

## Executive Summary

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

## Implementation Strategy

### Phase 1: Basic Optional Fields (MVP)

**Goals:**
- Add `?` syntax for primitive types
- Update parser to handle optional markers
- Modify validation to allow missing optional fields

**Changes Required:**

1. **Grammar Updates (`amino.abnf`)**
```abnf
field-definition = identifier ":" SP type [field-optional] [field-constraints] [comment]
field-optional = "?"
```

2. **Parser Changes (`amino/schema/parser.py`)**
```python
def _parse_field(self) -> FieldDefinition:
    """Parse a field definition with optional support."""
    name_token = self._expect(TokenType.WORD)
    self._expect(TokenType.COLON)
    
    # Parse the type
    type_info = self._parse_type_expression()
    field_type = type_info["type"]
    type_name = type_info["name"]
    element_types = type_info.get("element_types", [])
    
    # Handle optional type (ending with ?)
    optional = False
    peek_token = self._peek()
    if peek_token and peek_token.token_type == TokenType.QUESTION:
        optional = True
        self._advance()
    
    # ... rest of parsing logic
    
    return FieldDefinition(name_token.value, field_type, type_name, element_types, constraints, optional)
```

## Data Validation Semantics

### Missing vs Null Values

**Missing Field (Field not present in data):**
```json
{
  "name": "John",
  "age": 25
  // email is missing
}
```

**Null Field (Field present but null):**
```json
{
  "name": "John", 
  "age": 25,
  "email": null
}
```

**Validation Rules:**
1. **Required fields**: Must be present and non-null
2. **Optional fields**: Can be missing or null
3. **Optional with constraints**: If present and non-null, must satisfy constraints

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

## Migration Strategy

### Backward Compatibility
All existing schemas continue to work unchanged:
```amino
# Current schemas remain valid
name: Str
age: Int
active: Bool
```

### Gradual Adoption
```amino
# Phase 1: Add optional fields to existing schemas
name: Str      # Keep required fields as-is
age: Int       # Keep required fields as-is  
email: Str?    # Add new optional fields

# Phase 2: Convert appropriate fields to optional
name: Str      # Keep essential fields required
age: Int?      # Make non-essential fields optional
email: Str?    # Make non-essential fields optional
```

## Conclusion

Adding optional field support to amino is a foundational enhancement that will significantly improve its usability for real-world data validation scenarios. The `?` syntax is familiar to developers from many modern languages and provides a clear, concise way to express field optionality.