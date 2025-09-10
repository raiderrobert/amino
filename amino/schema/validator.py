"""Schema validation implementation."""

from typing import Any, Dict, List, Optional
from .ast import SchemaAST, FieldDefinition, StructDefinition
from .types import SchemaType
from ..utils.errors import SchemaParseError


class SchemaValidator:
    """Validates schema definitions."""
    
    def __init__(self, ast: SchemaAST):
        self.ast = ast
        self._field_names = {f.name for f in ast.fields}
        self._struct_names = {s.name for s in ast.structs}
        self._function_names = {f.name for f in ast.functions}
    
    def validate(self) -> List[str]:
        """Validate the schema AST and return list of errors."""
        errors = []
        
        # Check for duplicate names
        errors.extend(self._check_duplicates())
        
        # Validate field definitions
        for field in self.ast.fields:
            errors.extend(self._validate_field(field))
        
        # Validate struct definitions
        for struct in self.ast.structs:
            errors.extend(self._validate_struct(struct))
        
        # Validate function definitions
        for func in self.ast.functions:
            errors.extend(self._validate_function(func))
        
        return errors
    
    def _check_duplicates(self) -> List[str]:
        """Check for duplicate names across all definitions."""
        errors = []
        all_names = []
        
        # Collect all names
        all_names.extend([(f.name, "field") for f in self.ast.fields])
        all_names.extend([(s.name, "struct") for s in self.ast.structs])  
        all_names.extend([(f.name, "function") for f in self.ast.functions])
        all_names.extend([(name, "constant") for name in self.ast.constants])
        
        # Find duplicates
        seen = set()
        for name, kind in all_names:
            if name in seen:
                errors.append(f"Duplicate name '{name}' found")
            seen.add(name)
        
        return errors
    
    def _validate_field(self, field: FieldDefinition) -> List[str]:
        """Validate a field definition."""
        errors = []
        
        # Validate constraints based on type
        if field.field_type == SchemaType.int:
            errors.extend(self._validate_numeric_constraints(field))
        elif field.field_type == SchemaType.str:
            errors.extend(self._validate_string_constraints(field))
        elif field.field_type == SchemaType.list:
            errors.extend(self._validate_list_constraints(field))
        
        return errors
    
    def _validate_struct(self, struct: StructDefinition) -> List[str]:
        """Validate a struct definition."""
        errors = []
        
        # Check for duplicate field names within struct
        field_names = [f.name for f in struct.fields]
        if len(field_names) != len(set(field_names)):
            errors.append(f"Struct '{struct.name}' has duplicate field names")
        
        # Validate each field
        for field in struct.fields:
            errors.extend(self._validate_field(field))
        
        return errors
    
    def _validate_function(self, func) -> List[str]:
        """Validate a function definition."""
        errors = []
        
        # Validate default args reference valid constants or fields
        for arg in func.default_args:
            if (arg not in self.ast.constants and 
                arg not in self._field_names):
                errors.append(f"Function '{func.name}' references unknown default arg '{arg}'")
        
        return errors
    
    def _validate_numeric_constraints(self, field: FieldDefinition) -> List[str]:
        """Validate numeric type constraints."""
        errors = []
        
        if "min" in field.constraints and "max" in field.constraints:
            if field.constraints["min"] > field.constraints["max"]:
                errors.append(f"Field '{field.name}': min value greater than max value")
        
        return errors
    
    def _validate_string_constraints(self, field: FieldDefinition) -> List[str]:
        """Validate string type constraints."""
        errors = []
        
        valid_formats = {"email", "url", "uuid"}
        if "format" in field.constraints:
            fmt = field.constraints["format"]
            if fmt not in valid_formats:
                errors.append(f"Field '{field.name}': unknown format '{fmt}'")
        
        return errors
    
    def _validate_list_constraints(self, field: FieldDefinition) -> List[str]:
        """Validate list type constraints."""
        errors = []
        
        # Add list-specific validation here
        return errors