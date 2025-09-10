"""Type registry implementation."""

import dataclasses
from typing import Dict, Any, Callable, Optional, List, Union
from ..schema.types import SchemaType
from ..utils.errors import TypeValidationError


@dataclasses.dataclass
class TypeDefinition:
    """Definition of a custom type."""
    name: str
    base_type: Union[str, SchemaType]
    validator: Optional[Callable[[Any], bool]] = None
    constraints: Dict[str, Any] = dataclasses.field(default_factory=dict)
    format_string: Optional[str] = None
    description: Optional[str] = None


class TypeRegistry:
    """Registry for custom and built-in types."""
    
    def __init__(self):
        self._types: Dict[str, TypeDefinition] = {}
        self._validators: Dict[str, Callable] = {}
    
    def register_type(self, name: str, base_type: Union[str, SchemaType], 
                     validator: Optional[Callable] = None, 
                     format_string: Optional[str] = None,
                     description: Optional[str] = None,
                     **constraints) -> None:
        """Register a new custom type."""
        if name in self._types:
            raise TypeValidationError(f"Type '{name}' already registered")
        
        type_def = TypeDefinition(
            name=name,
            base_type=base_type,
            validator=validator,
            constraints=constraints,
            format_string=format_string,
            description=description
        )
        
        self._types[name] = type_def
        
        if validator:
            self._validators[name] = validator
    
    def get_type(self, name: str) -> Optional[TypeDefinition]:
        """Get type definition by name."""
        return self._types.get(name)
    
    def has_type(self, name: str) -> bool:
        """Check if type is registered."""
        return name in self._types
    
    def get_validator(self, type_name: str) -> Optional[Callable]:
        """Get validator function for a type."""
        return self._validators.get(type_name)
    
    def validate_value(self, type_name: str, value: Any) -> bool:
        """Validate a value against a type."""
        type_def = self.get_type(type_name)
        if not type_def:
            # Check if it's a built-in type
            return self._validate_builtin_type(type_name, value)
        
        # Validate base type first
        base_valid = True
        if isinstance(type_def.base_type, str):
            base_valid = self.validate_value(type_def.base_type, value)
        elif isinstance(type_def.base_type, SchemaType):
            base_valid = self._validate_schema_type(type_def.base_type, value)
        
        if not base_valid:
            return False
        
        # Apply custom validator if present
        if type_def.validator:
            try:
                return type_def.validator(value)
            except Exception:
                return False
        
        # Apply constraints
        return self._validate_constraints(type_def.constraints, value)
    
    def list_types(self) -> List[str]:
        """List all registered type names."""
        return list(self._types.keys())
    
    def remove_type(self, name: str) -> bool:
        """Remove a type from registry."""
        if name in self._types:
            del self._types[name]
            if name in self._validators:
                del self._validators[name]
            return True
        return False
    
    def _validate_builtin_type(self, type_name: str, value: Any) -> bool:
        """Validate against built-in types."""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "any": lambda x: True
        }
        
        if type_name in type_map:
            expected_type = type_map[type_name]
            if type_name == "any":
                return expected_type(value)  # Lambda function
            elif type_name == "float":
                return isinstance(value, (int, float))
            else:
                return isinstance(value, expected_type)
        
        return False
    
    def _validate_schema_type(self, schema_type: SchemaType, value: Any) -> bool:
        """Validate against SchemaType enum."""
        if schema_type == SchemaType.str:
            return isinstance(value, str)
        elif schema_type == SchemaType.int:
            return isinstance(value, int)
        elif schema_type == SchemaType.float:
            return isinstance(value, (int, float))
        elif schema_type == SchemaType.bool:
            return isinstance(value, bool)
        elif schema_type == SchemaType.any:
            return True
        elif schema_type == SchemaType.list:
            return isinstance(value, list)
        else:
            return False
    
    def _validate_constraints(self, constraints: Dict[str, Any], value: Any) -> bool:
        """Validate value against constraints."""
        for constraint, constraint_value in constraints.items():
            if constraint == "min":
                if hasattr(value, '__lt__') and value < constraint_value:
                    return False
            elif constraint == "max":
                if hasattr(value, '__gt__') and value > constraint_value:
                    return False
            elif constraint == "length":
                if hasattr(value, '__len__') and len(value) != constraint_value:
                    return False
            elif constraint == "format":
                # Format validation would go here
                pass
            # Add more constraint types as needed
        
        return True