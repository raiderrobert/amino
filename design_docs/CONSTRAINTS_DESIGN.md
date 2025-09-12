# Amino Constraints System Design

## Summary

This document outlines the design for extending amino's constraint validation system from its current basic support to a comprehensive, extensible validation framework. Based on research of 10+ modern validation libraries and schema languages, this design provides a roadmap for enhancing amino's expressiveness while maintaining its simplicity.

## Current State Analysis

### What Works Today

Amino currently supports only using types as a constraint:
```amino
age: Int
name: Str
email: Str
```

### Current Limitations

1. **Limited Constraint Types**: Only types are supported
2. **Basic Error Messages**: No context or field path information
3. **No Composition**: Can only do unions on types
4. **No Custom Validation**: No extensibility mechanism
5. **No Cross-Field Validation**: Cannot validate relationships between fields
6. **No Conditional Logic**: Cannot apply constraints based on other field values

## Research Foundation

Analysis of modern constraint systems (JSON Schema, Joi, Pydantic, Zod, etc.) reveals these patterns:

### Common Constraint Categories
1. **Range/Boundary**: `min`, `max`, `between`, `exclusiveMin`, `exclusiveMax`
2. **Size/Length**: `minLength`, `maxLength`, `minItems`, `maxItems`
3. **Format/Pattern**: `pattern`, `format`, `email`, `url`, `uuid`
4. **Enumeration**: `oneOf`, `enum`, `const`
5. **Structural**: `required`, `unique`, `dependencies`
6. **Custom Logic**: `validate`, `when`, `if`

### Best Practices Identified
- **Declarative over imperative** constraint syntax
- **Composable constraints** that work together naturally
- **Rich error context** with field paths and expected values
- **Extensible architecture** for custom validation
- **Early vs complete validation** strategies

## Design Alternatives

### Constraint Syntax Options

**Block syntax (chosen):**
```amino
age: Int {min: 18, max: 120}
```

**Inline syntax (alternative):**
```amino
age: Int(min=18, max=120)
```

**Annotation syntax (alternative):**
```amino
age: Int @min(18) @max(120)
```

**Rationale**: Block syntax clearly separates type from constraints and scales better for multiple constraints.

### Multiple Constraint Combination

**AND logic (chosen):**
```amino
username: Str {minLength: 3, maxLength: 20, pattern: "^[a-zA-Z0-9_]+$"}
```

**Explicit boolean logic (alternative):**
```amino
username: Str {and: [minLength: 3, maxLength: 20, pattern: "^[a-zA-Z0-9_]+$"]}
```

**Rationale**: Implicit AND is simpler and covers 95% of use cases. Complex boolean logic can be added later if needed.

### Range Constraint Patterns

**Separate min/max (chosen):**
```amino
age: Int {min: 18, max: 120}
```

**Range syntax (alternative):**
```amino
age: Int {range: [18, 120]}
```

**Between syntax (alternative):**
```amino
age: Int {between: [18, 120]}
```

**Rationale**: Separate min/max allows partial bounds and is more familiar from existing validation libraries.

### Pattern vs Format Constraints

**Pattern-based (flexible):**
```amino
email: Str {pattern: "^[^@]+@[^@]+\\.[^@]+$"}
```

**Format-based (structured):**
```amino
email: Str {format: "email"}
```

**Mixed approach (chosen):** Support both, with format for common patterns and pattern for custom validation.

### Cross-Field Validation Approaches

**Expression-based:**
```amino
total: Float {equals: "tax + shipping + subtotal"}
```

**Reference-based:**
```amino
confirm_password: Str {equals: password}
```

**Function-based:**
```amino
age: Int {consistentWith: birth_date, validator: "age_from_birthdate"}
```

**Decision**: Start with simple reference-based, add expression support later.

## Core Constraint Types

### Numeric Constraints
```amino
# Range constraints
age: Int {min: 18, max: 120}
score: Float {min: 0.0, max: 100.0}
temperature: Int {exclusiveMin: -273, exclusiveMax: 1000}
```

### String Constraints
```amino
# Length constraints  
name: Str {minLength: 2, maxLength: 50}
code: Str {exactLength: 6}

# Pattern constraints
email: Str {pattern: "^[^@]+@[^@]+\\.[^@]+$"}
phone: Str {pattern: "\\+?\\d{10,15}"}
```

### Collection Constraints
```amino
# List constraints
tags: List[Str] {minItems: 1, maxItems: 10}
scores: List[Int] {exactItems: 5}

# Uniqueness constraints
items: List[Str] {unique: true}
```

### Choice Constraints
```amino
# Enumeration constraints
status: Str {oneOf: ["active", "inactive", "pending"]}
priority: Int {oneOf: [1, 2, 3, 4, 5]}
```

### Advanced Features

**Multiple constraints:**
```amino
username: Str {minLength: 3, maxLength: 20, pattern: "^[a-zA-Z0-9_]+$"}
```

**Cross-field validation:**
```amino
struct User {
    birth_date: Str,
    age: Int {consistentWith: birth_date}
}
```

**Custom validators:**
```amino
work_email: Str {custom: "company_domain_check"}
```

## Grammar Impact

**Current constraint syntax:**
```abnf
field-constraints = "{" SP constraint *("," SP constraint) SP "}"
constraint = constraint-name ":" SP constraint-value
```

**Extended constraint syntax:**
```abnf
constraint-name = "min" / "max" / "exclusiveMin" / "exclusiveMax" /
                  "minLength" / "maxLength" / "exactLength" / 
                  "minItems" / "maxItems" / "exactItems" /
                  "pattern" / "oneOf" / "unique" / "custom"
constraint-value = number / string / array / boolean
```

## Implementation Impact

This feature will require changes to:
- Parser: Parse constraint blocks and validate constraint syntax
- Validation Engine: Apply constraint validation logic
- Error Reporting: Provide detailed constraint violation messages
- Type System: Track constraint metadata alongside type information

## Backward Compatibility

All existing schemas continue to work unchanged:
- Current basic constraints remain supported  
- No breaking changes to existing constraint syntax
- New constraint types are additive

## Examples

### E-commerce Product Validation
```amino
struct Product {
    id: Str {format: "uuid"},
    name: Str {minLength: 1, maxLength: 200},
    price: Float {min: 0.01, max: 999999.99},
    category: Str {oneOf: ["electronics", "clothing", "books", "home"]},
    tags: List[Str] {minItems: 1, maxItems: 10, unique: true},
    sku: Str {pattern: "^[A-Z]{2}\\d{6}$"},
    weight: Float? {min: 0.01, max: 1000.0},
    dimensions: List[Float] {exactItems: 3}  # [length, width, height]
}
```

### User Registration Validation
```amino
struct UserRegistration {
    username: Str {
        minLength: 3, 
        maxLength: 20, 
        pattern: "^[a-zA-Z0-9_]+$"
    },
    email: Str {format: "email"},
    password: Str {
        minLength: 8,
        pattern: "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$"
    },
    age: Int {min: 13, max: 120},
    interests: List[Str] {
        minItems: 1,
        maxItems: 5,
        unique: true
    },
    terms_accepted: Bool {const: true}
}
```

### API Configuration Validation
```amino
struct APIConfig {
    version: Str {oneOf: ["v1", "v2", "v2.1"]},
    timeout: Int {min: 1000, max: 300000},  # milliseconds
    retries: Int {between: [0, 5]},
    endpoints: List[Str] {
        minItems: 1,
        unique: true
    },
    rate_limit: Int {min: 1, max: 10000}  # requests per minute
}
```

## Benefits

### For Schema Authors
- **Comprehensive Validation**: Express complex validation rules declaratively
- **Better Error Messages**: Get precise, actionable error information
- **Reduced Boilerplate**: Built-in validators for common patterns
- **Documentation**: Constraints serve as inline documentation

### For Application Developers
- **Runtime Safety**: Catch invalid data before it causes issues
- **API Validation**: Validate incoming data against schemas
- **Configuration Validation**: Ensure config files meet requirements
- **Data Quality**: Maintain data integrity across systems

### For Tools and IDEs
- **Static Analysis**: Detect constraint violations during development
- **Auto-completion**: Suggest valid values based on constraints
- **Documentation Generation**: Generate constraint documentation
- **Test Data Generation**: Generate valid test data from constraints

## Trade-offs and Considerations

### Expressiveness vs Complexity
- **Pro**: Rich constraint vocabulary covers most validation needs
- **Con**: More concepts for users to learn and validate
- **Decision**: Start with essential constraints, add complexity gradually

### Performance vs Features
- **Pro**: Detailed validation catches more data quality issues
- **Con**: More validation overhead, especially for complex constraints
- **Decision**: Optimize common constraints, allow users to opt into expensive ones

### Flexibility vs Consistency
- **Pro**: Custom validators allow domain-specific validation logic
- **Con**: Can lead to inconsistent validation approaches across schemas
- **Decision**: Provide rich built-in constraints, custom validators for edge cases

### Error Detail vs Simplicity
- **Pro**: Detailed error messages help debugging
- **Con**: Verbose errors can be overwhelming
- **Decision**: Structured errors with optional detail levels

## Conclusion

This design provides a comprehensive roadmap for evolving amino's constraint system from basic validation to a powerful, extensible framework. By following proven patterns from successful validation libraries while maintaining amino's simplicity, we can provide users with the tools they need for robust data validation.

The phased approach ensures manageable implementation while delivering value at each stage. The emphasis on backward compatibility and gradual enhancement allows existing users to adopt new features at their own pace while providing powerful new capabilities for complex validation scenarios.