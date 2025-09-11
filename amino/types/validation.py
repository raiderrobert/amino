"""Type validation implementation."""

import dataclasses
from typing import Any, List, Optional, Dict, Union
from .registry import TypeRegistry
from ..schema.ast import SchemaAST, FieldDefinition
from ..schema.types import SchemaType
from ..utils.errors import TypeValidationError


@dataclasses.dataclass
class ValidationError:
    """Individual validation error."""
    field: str
    message: str
    value: Any = None


@dataclasses.dataclass
class ValidationResult:
    """Result of type validation."""
    valid: bool
    errors: List[ValidationError] = dataclasses.field(default_factory=list)
    
    def add_error(self, field: str, message: str, value: Any = None):
        """Add a validation error."""
        self.valid = False
        self.errors.append(ValidationError(field, message, value))


class TypeValidator:
    """Validates data against schema with custom types."""
    
    def __init__(self, schema_ast: SchemaAST, type_registry: TypeRegistry = None):
        self.schema_ast = schema_ast
        self.type_registry = type_registry or TypeRegistry()
    
    def validate_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate data against the schema."""
        result = ValidationResult(valid=True)
        
        # Validate top-level fields
        for field_def in self.schema_ast.fields:
            self._validate_field(field_def, data, result)
        
        # Validate struct fields if present
        for struct_def in self.schema_ast.structs:
            if struct_def.name in data:
                struct_data = data[struct_def.name]
                if not isinstance(struct_data, dict):
                    result.add_error(struct_def.name, 
                                   f"Expected object for struct '{struct_def.name}'", 
                                   struct_data)
                    continue
                
                for field_def in struct_def.fields:
                    self._validate_field(field_def, struct_data, result, 
                                       prefix=f"{struct_def.name}.")
        
        return result
    
    def validate_field_value(self, field_name: str, value: Any) -> ValidationResult:
        """Validate a single field value."""
        result = ValidationResult(valid=True)
        
        # Find field definition
        field_def = None
        for field in self.schema_ast.fields:
            if field.name == field_name:
                field_def = field
                break
        
        if not field_def:
            result.add_error(field_name, f"Unknown field '{field_name}'")
            return result
        
        self._validate_field_value(field_def, value, result, field_name)
        return result
    
    def _validate_field(self, field_def: FieldDefinition, data: Dict[str, Any], 
                       result: ValidationResult, prefix: str = ""):
        """Validate a field against its definition."""
        full_field_name = f"{prefix}{field_def.name}"
        
        # Check if field is present
        if field_def.name not in data:
            if not field_def.optional:
                result.add_error(full_field_name, f"Required field '{full_field_name}' missing")
            return
        
        value = data[field_def.name]
        
        # Check for null/None values on optional fields
        if value is None and field_def.optional:
            return
        
        self._validate_field_value(field_def, value, result, full_field_name)
    
    def _validate_field_value(self, field_def: FieldDefinition, value: Any, 
                             result: ValidationResult, field_name: str):
        """Validate a field value against its type and constraints."""
        
        # Handle list types
        if field_def.field_type.value == "list":
            if not isinstance(value, list):
                result.add_error(field_name, f"Expected list for field '{field_name}'", value)
                return
            
            # TODO: Validate list element types
            return
        
        # Handle custom types first
        if field_def.field_type == SchemaType.custom:
            # Use the preserved type_name for custom types
            type_name = field_def.type_name
            if not self.type_registry.validate_value(type_name, value):
                result.add_error(field_name, 
                               f"Value does not match type '{type_name}'", value)
            return
        
        # Handle registered types that are built-in
        type_name = field_def.field_type.value
        if self.type_registry.has_type(type_name):
            if not self.type_registry.validate_value(type_name, value):
                result.add_error(field_name, 
                               f"Value does not match type '{type_name}'", value)
            return
        
        # Handle built-in types
        if not self._validate_builtin_type(field_def.field_type.value, value):
            result.add_error(field_name, 
                           f"Expected {field_def.field_type.value} for field '{field_name}'", 
                           value)
            return
        
        # Validate constraints
        self._validate_constraints(field_def, value, result, field_name)
    
    def _validate_builtin_type(self, type_name: str, value: Any) -> bool:
        """Validate against built-in types."""
        type_validators = {
            "str": lambda x: isinstance(x, str),
            "int": lambda x: isinstance(x, int),
            "float": lambda x: isinstance(x, (int, float)),
            "bool": lambda x: isinstance(x, bool),
            "decimal": lambda x: isinstance(x, (int, float)),
            "any": lambda x: True,
        }
        
        validator = type_validators.get(type_name)
        return validator(value) if validator else False
    
    def _validate_constraints(self, field_def: FieldDefinition, value: Any, 
                             result: ValidationResult, field_name: str):
        """Validate field constraints."""
        for constraint, constraint_value in field_def.constraints.items():
            if constraint == "min":
                if hasattr(value, '__lt__') and value < constraint_value:
                    result.add_error(field_name, 
                                   f"Value {value} is less than minimum {constraint_value}")
            
            elif constraint == "max":
                if hasattr(value, '__gt__') and value > constraint_value:
                    result.add_error(field_name, 
                                   f"Value {value} is greater than maximum {constraint_value}")
            
            elif constraint == "length":
                if hasattr(value, '__len__') and len(value) != constraint_value:
                    result.add_error(field_name, 
                                   f"Length {len(value)} does not equal required {constraint_value}")
            
            elif constraint == "format":
                # Format validation using built-in validators
                if constraint_value == "email":
                    from .builtin import BuiltinTypes
                    if not BuiltinTypes.validate_email(value):
                        result.add_error(field_name, f"Invalid email format: {value}")
                
                elif constraint_value == "url":
                    from .builtin import BuiltinTypes  
                    if not BuiltinTypes.validate_url(value):
                        result.add_error(field_name, f"Invalid URL format: {value}")
                
                elif constraint_value == "uuid":
                    from .builtin import BuiltinTypes
                    if not BuiltinTypes.validate_uuid(value):
                        result.add_error(field_name, f"Invalid UUID format: {value}")