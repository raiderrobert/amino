# Amino Constraints System Design

## Executive Summary

This document outlines the design for extending amino's constraint validation system from its current basic support to a comprehensive, extensible validation framework. Based on research of 10+ modern validation libraries and schema languages, this design provides a roadmap for enhancing amino's expressiveness while maintaining its simplicity.

## Current State Analysis

### What Works Today

Amino currently supports basic constraints with this syntax:
```amino
age: Int {min: 18, max: 120}
name: Str {length: 5}
email: Str {format: "email"}
```

**Implemented Constraints:**
- `min`, `max` - Numeric range validation
- `length` - Exact string/list length
- `format` - Limited format validation (`email`, `url`, `uuid`)

**Current Architecture:**
- Grammar support: `field-constraints = "{" SP *(constraint SP) "}"`
- Parser: `_parse_constraints()` in `amino/schema/parser.py`
- Validation: `_validate_constraints()` in `amino/types/validation.py`
- Storage: `constraints: dict[str, Any]` in `FieldDefinition`

### Current Limitations

1. **Limited Constraint Types**: Only 4 constraint types supported
2. **Basic Error Messages**: No context or field path information
3. **No Composition**: Cannot combine multiple constraints meaningfully
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

## Proposed Design

### Phase 1: Enhanced Core Constraints

Expand the basic constraint set with commonly needed validations:

```amino
# Range constraints
age: Int {min: 18, max: 120}
score: Float {between: [0.0, 100.0]}
temperature: Int {exclusiveMin: -273, exclusiveMax: 1000}

# Length constraints  
name: Str {minLength: 2, maxLength: 50}
tags: List[Str] {minItems: 1, maxItems: 10}
code: Str {exactLength: 6}

# Pattern constraints
email: Str {pattern: "^[^@]+@[^@]+\\.[^@]+$"}
phone: Str {pattern: "\\+?\\d{10,15}"}

# Enumeration constraints
status: Str {oneOf: ["active", "inactive", "pending"]}
priority: Int {oneOf: [1, 2, 3, 4, 5]}

# Format constraints (expanded)
website: Str {format: "url"}
user_id: Str {format: "uuid"}
birth_date: Str {format: "date"}
ip_address: Str {format: "ipv4"}

# Uniqueness constraints
items: List[Str] {unique: true}
```

### Phase 2: Constraint Composition

Allow multiple constraints on single fields with clear combination rules:

```amino
# Multiple constraints combine with AND logic
username: Str {minLength: 3, maxLength: 20, pattern: "^[a-zA-Z0-9_]+$"}
price: Float {min: 0.01, max: 999999.99, precision: 2}
tags: List[Str] {minItems: 1, maxItems: 5, unique: true}

# Constraint precedence and conflict resolution
password: Str {
    minLength: 8,
    pattern: "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$",
    maxLength: 128
}
```

### Phase 3: Cross-Field Validation

Enable constraints that reference other fields:

```amino
struct User {
    birth_date: Str {format: "date"},
    age: Int {min: 0, max: 150},
    # Cross-field constraint
    age: Int {consistentWith: "birth_date"}
}

struct Order {
    total: Float,
    tax: Float,
    shipping: Float,
    # Ensure total equals sum of parts
    total: Float {equals: "tax + shipping + subtotal"}
}

# Conditional constraints
struct Account {
    account_type: Str {oneOf: ["personal", "business"]},
    ssn: Str? {requiredIf: "account_type == 'personal'"},
    tax_id: Str? {requiredIf: "account_type == 'business'"}
}
```

### Phase 4: Custom Validators

Provide extensibility for complex business logic:

```amino
# Custom validator registration
validator email_domain_check(email: Str) -> Bool {
    # Custom logic here
    return email.endsWith("@company.com")
}

# Usage in constraints
work_email: Str {format: "email", custom: "email_domain_check"}

# Inline lambda-style validators (future)
age: Int {validate: "value >= 18 and value <= 120"}
```

## Implementation Strategy

### Phase 1: Enhanced Core Constraints

**Goals:**
- Expand constraint vocabulary to ~15 essential constraint types
- Improve error messages with context
- Ensure backward compatibility

**Changes Required:**

1. **Grammar Updates (`amino.abnf`)**
```abnf
constraint = constraint-name ":" SP constraint-value
constraint-name = "min" / "max" / "between" / "exclusiveMin" / "exclusiveMax" /
                  "minLength" / "maxLength" / "exactLength" / 
                  "minItems" / "maxItems" / 
                  "pattern" / "format" / "oneOf" / "unique"
constraint-value = number / string / array / boolean
array = "[" SP constraint-value *("," SP constraint-value) SP "]"
```

2. **Validation Engine (`amino/types/validation.py`)**
```python
def _validate_constraints(self, field_def: FieldDefinition, value: Any, result: ValidationResult, field_name: str):
    """Enhanced constraint validation with better error context."""
    for constraint_name, constraint_value in field_def.constraints.items():
        try:
            if not self._apply_constraint(constraint_name, constraint_value, value, field_name):
                error_msg = self._format_constraint_error(
                    constraint_name, constraint_value, value, field_name
                )
                result.add_error(field_name, error_msg, value)
        except ConstraintError as e:
            result.add_error(field_name, str(e), value)

def _apply_constraint(self, name: str, constraint_value: Any, value: Any, field_name: str) -> bool:
    """Apply individual constraint with detailed validation logic."""
    constraint_validators = {
        "min": lambda v, c: hasattr(v, "__ge__") and v >= c,
        "max": lambda v, c: hasattr(v, "__le__") and v <= c,
        "between": lambda v, c: len(c) == 2 and c[0] <= v <= c[1],
        "minLength": lambda v, c: hasattr(v, "__len__") and len(v) >= c,
        "maxLength": lambda v, c: hasattr(v, "__len__") and len(v) <= c,
        "pattern": lambda v, c: isinstance(v, str) and re.match(c, v),
        "oneOf": lambda v, c: v in c,
        "unique": self._validate_unique_items,
        # ... more validators
    }
    
    validator = constraint_validators.get(name)
    if not validator:
        raise ConstraintError(f"Unknown constraint: {name}")
    
    return validator(value, constraint_value)
```

3. **Enhanced Error Reporting**
```python
@dataclasses.dataclass
class ValidationError:
    field: str
    message: str
    value: Any = None
    constraint_name: str | None = None
    constraint_value: Any = None
    field_path: list[str] = dataclasses.field(default_factory=list)
```

### Phase 2: Parser and Grammar Extensions

**Enhanced Constraint Parsing:**
```python
def _parse_constraints(self) -> dict[str, Any]:
    """Enhanced constraint parsing with type validation."""
    # ... existing code ...
    
    # Validate constraint-type compatibility
    if key_token.value in ("min", "max") and not isinstance(parsed_value, (int, float)):
        raise SchemaParseError(f"Constraint '{key_token.value}' requires numeric value")
    
    # Handle array constraints
    if key_token.value in ("oneOf", "between"):
        if not isinstance(parsed_value, list):
            raise SchemaParseError(f"Constraint '{key_token.value}' requires array value")
```

### Phase 3: Architecture Enhancements

**Constraint Registry System:**
```python
class ConstraintRegistry:
    """Registry for constraint validators."""
    
    def __init__(self):
        self._validators: dict[str, Callable] = {}
        self._register_builtin_constraints()
    
    def register_constraint(self, name: str, validator: Callable, 
                          compatible_types: list[SchemaType] = None):
        """Register custom constraint validator."""
        self._validators[name] = ConstraintValidator(
            name=name,
            validator=validator,
            compatible_types=compatible_types or []
        )
    
    def validate_constraint(self, name: str, value: Any, constraint_value: Any) -> bool:
        """Apply constraint validation."""
        if name not in self._validators:
            raise ConstraintError(f"Unknown constraint: {name}")
        return self._validators[name].validate(value, constraint_value)
```

## Detailed Constraint Specifications

### Numeric Constraints
```amino
# Basic range
age: Int {min: 18, max: 120}
score: Float {min: 0.0, max: 100.0}

# Exclusive bounds
temperature: Float {exclusiveMin: -273.15, exclusiveMax: 1000.0}

# Range with single expression
rating: Int {between: [1, 5]}
```

### String Constraints
```amino
# Length constraints
name: Str {minLength: 2, maxLength: 50}
code: Str {exactLength: 6}

# Pattern matching
email: Str {pattern: "^[^@]+@[^@]+\\.[^@]+$"}
phone: Str {pattern: "\\+?\\d{10,15}"}

# Format validation
website: Str {format: "url"}
user_id: Str {format: "uuid"}
```

### Collection Constraints
```amino
# List size
tags: List[Str] {minItems: 1, maxItems: 10}
scores: List[Int] {exactItems: 5}

# Uniqueness
categories: List[Str] {unique: true}
```

### Choice Constraints
```amino
# Enumeration
status: Str {oneOf: ["active", "inactive", "pending"]}
priority: Int {oneOf: [1, 2, 3, 4, 5]}

# Single value
api_version: Str {const: "v2.1"}
```

## Error Message Design

### Current Error Messages
```
"Value 15 is less than minimum 18"
"Length 3 does not equal required 5"
```

### Enhanced Error Messages
```
"Field 'user.age' (15) violates constraint 'min': must be >= 18"
"Field 'user.name' (length 3) violates constraint 'exactLength': must be exactly 5 characters"
"Field 'user.tags' violates constraint 'unique': duplicate values found [tag1, tag1]"
"Field 'user.email' ('invalid') violates constraint 'pattern': must match '^[^@]+@[^@]+\\.[^@]+$'"
```

### Error Context Structure
```python
@dataclasses.dataclass
class ConstraintViolation:
    field_path: str
    constraint_name: str
    constraint_value: Any
    actual_value: Any
    message: str
    suggestions: list[str] = dataclasses.field(default_factory=list)
```

## Migration Strategy

### Backward Compatibility
All existing schemas continue to work unchanged:
```amino
# Current syntax remains valid
age: Int {min: 18, max: 120}
name: Str {length: 5}
email: Str {format: "email"}
```

### Gradual Enhancement
```amino
# Phase 1: Enhanced constraints
age: Int {min: 18, max: 120}  # existing
username: Str {minLength: 3, maxLength: 20, pattern: "^[a-zA-Z0-9_]+$"}  # new

# Phase 2: Multiple constraints
password: Str {minLength: 8, pattern: "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$"}

# Phase 3: Cross-field validation (future)
struct User {
    birth_date: Str {format: "date"},
    age: Int {consistentWith: "birth_date"}
}
```

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

## Implementation Phases

### Phase 1 (MVP): Enhanced Core Constraints
- **Timeline**: 2-3 weeks
- **Scope**: 15 essential constraint types, improved error messages
- **Deliverables**: Enhanced validation engine, expanded grammar

### Phase 2: Composition and Advanced Features
- **Timeline**: 3-4 weeks  
- **Scope**: Multiple constraints per field, better error context
- **Deliverables**: Constraint composition, rich error reporting

### Phase 3: Extensibility
- **Timeline**: 4-5 weeks
- **Scope**: Custom validators, cross-field validation
- **Deliverables**: Plugin system, conditional constraints

### Phase 4: Developer Experience
- **Timeline**: 2-3 weeks
- **Scope**: Tool integration, documentation generation
- **Deliverables**: IDE support, schema documentation tools

## Success Metrics

### Adoption Metrics
- Percentage of schemas using enhanced constraints
- Number of constraint types actively used
- Reduction in validation-related bugs

### Quality Metrics
- Improved error message clarity (user feedback)
- Faster debugging of validation issues
- Better data quality in production

### Technical Metrics
- Validation performance impact
- Memory usage of constraint system
- Test coverage of constraint functionality

## Risks and Considerations

### Complexity Management
- **Risk**: Feature creep making the system too complex
- **Mitigation**: Phased approach, focus on common use cases first

### Performance Impact
- **Risk**: Complex constraints slowing down validation
- **Mitigation**: Benchmarking, optimization, lazy evaluation

### Backward Compatibility
- **Risk**: Breaking changes to existing schemas
- **Mitigation**: Strict backward compatibility, deprecation path

### Error Message Quality
- **Risk**: Cryptic or overwhelming error messages
- **Mitigation**: User testing, clear message templates

## Conclusion

This design provides a comprehensive roadmap for evolving amino's constraint system from basic validation to a powerful, extensible framework. By following proven patterns from successful validation libraries while maintaining amino's simplicity, we can provide users with the tools they need for robust data validation.

The phased approach ensures manageable implementation while delivering value at each stage. The emphasis on backward compatibility and gradual enhancement allows existing users to adopt new features at their own pace while providing powerful new capabilities for complex validation scenarios.