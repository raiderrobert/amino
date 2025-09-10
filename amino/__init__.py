"""Amino - Schema-first classification rules engine."""

# Main API
from .core import Schema, load_schema

# Type system
from .types import TypeRegistry, register_builtin_types

# Utilities  
from .utils.errors import (
    AminoError, SchemaParseError, RuleParseError, 
    TypeValidationError, RuleEvaluationError
)

__version__ = "0.1.0"

__all__ = [
    # Main API
    'Schema',
    'load_schema',
    
    # Type system
    'TypeRegistry', 
    'register_builtin_types',
    
    # Errors
    'AminoError',
    'SchemaParseError', 
    'RuleParseError',
    'TypeValidationError',
    'RuleEvaluationError'
]
