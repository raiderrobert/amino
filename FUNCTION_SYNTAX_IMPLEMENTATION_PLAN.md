# Amino Schema Function Syntax Implementation Plan

## Overview

This document outlines the implementation plan for updating Amino Schema function syntax to support named parameters while removing default argument support. The changes will make function declarations more self-documenting and consistent with modern language patterns.

## Current vs. New Syntax

### Current Syntax
```
function_name: (type1, type2) -> return_type
function_with_defaults: (DEFAULT_ARG)(type1, type2) -> return_type
```

### New Syntax
```
function_name: (param1_name: type1, param2_name: type2) -> return_type
```

## Implementation Steps

### 1. Update AST Definitions

**File:** `amino/schema/ast.py:28-34`

**Changes Required:**
- Create new `FunctionParameter` dataclass to represent named parameters
- Update `FunctionDefinition` to use `parameters` list instead of `input_types`
- Remove `default_args` field

**Implementation:**
```python
@dataclasses.dataclass
class FunctionParameter:
    """Represents a function parameter in a function declaration."""
    name: str
    param_type: SchemaType

@dataclasses.dataclass
class FunctionDefinition:
    """Represents a function declaration in the schema."""
    name: str
    parameters: list[FunctionParameter]  # Replace input_types
    output_type: SchemaType
    # Remove default_args field entirely
```

### 2. Update Parser Logic

**File:** `amino/schema/parser.py:202-243`

**Changes Required:**
- Remove default argument parsing logic (lines 207-225)
- Update parameter parsing to capture parameter names with types
- Simplify function detection logic

**Key Changes:**
- Remove the complex lookahead logic for detecting default arguments
- Update `_parse_function()` method to parse `name: type` patterns
- Update `_is_function_declaration()` to remove default argument detection

**New Parser Logic:**
```python
def _parse_function(self) -> FunctionDefinition:
    """Parse a function declaration with named parameters."""
    name_token = self._expect(TokenType.WORD)
    self._expect(TokenType.COLON)
    self._expect(TokenType.LPAREN)
    
    parameters = []
    while self._peek() and self._peek().token_type != TokenType.RPAREN:
        # Parse parameter name
        param_name_token = self._expect(TokenType.WORD)
        self._expect(TokenType.COLON)
        
        # Parse parameter type
        param_type_token = self._expect(TokenType.WORD)
        param_type = parse_type(param_type_token.value, self.strict, self.known_custom_types)
        
        parameters.append(FunctionParameter(param_name_token.value, param_type))
        
        # Handle comma separator
        if self._peek() and self._peek().token_type == TokenType.COMMA:
            self._advance()
    
    self._expect(TokenType.RPAREN)
    self._expect(TokenType.ARROW)
    
    # Parse output type
    output_token = self._expect(TokenType.WORD)
    output_type = parse_type(output_token.value, self.strict, self.known_custom_types)
    
    return FunctionDefinition(name_token.value, parameters, output_type)
```

### 3. Update Test Cases

**File:** `tests/test_advanced_schema_features.py`

**Changes Required:**

1. **Update test expectations** (lines 28, 38, 48-49, 62, 84-89):
   - Replace `input_types` assertions with `parameters` assertions
   - Remove `default_args` assertions
   - Update expected function structures

2. **Remove default argument test cases** (lines 32-41):
   - Remove test case with `(MAX_AMOUNT)(int)` syntax
   - Remove assertions checking for `default_args`

3. **Update function evaluation tests** (lines 157-166):
   - Ensure function implementations work with new parameter structure
   - Update any code that relies on `input_types` to use `parameters`

**Example Test Updates:**
```python
# OLD
assert func.input_types == [SchemaType.int, SchemaType.float]
assert func.default_args == []

# NEW
assert len(func.parameters) == 2
assert func.parameters[0].name == "amount"
assert func.parameters[0].param_type == SchemaType.int
assert func.parameters[1].name == "rate" 
assert func.parameters[1].param_type == SchemaType.float
```

### 4. Update Runtime Components

**Files to Check and Update:**
- `amino/runtime/evaluator.py` - Function call evaluation
- `amino/runtime/engine.py` - Function registration
- `amino/core.py` - Schema loading and function handling

**Potential Changes:**
- Update any code that accesses `input_types` to use `parameters`
- Update function signature validation
- Update error messages to reference parameter names

### 5. Update Documentation Examples

**File:** `README.md:148-194`

**Changes Required:**
- Update function syntax examples to use named parameters
- Remove default argument examples and explanations
- Update code examples to match new syntax

**Example Updates:**
```markdown
# OLD
smallest_number: (int, int) -> int
within_tolerances: (COMPANY_MAX_LOAN_AMT)(int, int) -> bool

# NEW  
smallest_number: (first: int, second: int) -> int
calculate_tax: (amount: int, rate: float) -> float
```

## Implementation Order

1. **Phase 1**: Update AST definitions (`ast.py`)
2. **Phase 2**: Update parser logic (`parser.py`) 
3. **Phase 3**: Update and fix all test cases
4. **Phase 4**: Update runtime components if needed
5. **Phase 5**: Update documentation and examples

## Backward Compatibility

**Breaking Changes:**
- All existing schemas using the old syntax will need to be updated
- Schemas using default arguments `(DEFAULT_ARG)(...)` syntax will no longer work
- Any code accessing `input_types` or `default_args` attributes will break

**Migration Required:**
- Convert `function_name: (type1, type2) -> return_type` to `function_name: (param1: type1, param2: type2) -> return_type`
- Remove any default argument usage and pass values explicitly
- Update any code that inspects function metadata

## Testing Strategy

1. **Unit Tests**: Update all existing parser and AST tests
2. **Integration Tests**: Verify function evaluation still works end-to-end
3. **Regression Tests**: Ensure no other schema features are broken
4. **Error Handling**: Test parsing errors with invalid syntax

## Expected Benefits

1. **Self-documenting**: Parameter names clarify function usage
2. **Simplified Implementation**: Single parsing path, no default argument complexity
3. **Modern Syntax**: Consistent with TypeScript, Rust, and other modern languages
4. **Better Tooling**: Parameter names enable better IDE support and error messages

## Risk Assessment

**Low Risk:**
- Changes are localized to parsing and AST representation
- Core runtime evaluation logic should remain largely unchanged
- Strong test coverage exists

**Mitigation:**
- Implement changes incrementally
- Run full test suite after each phase
- Keep runtime changes minimal