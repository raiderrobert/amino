"""Amino - Schema-first classification rules engine."""

from .core import Schema, load_schema

from .types import TypeRegistry, register_builtin_types

from .utils.errors import (
    AminoError, SchemaParseError, RuleParseError, 
    TypeValidationError, RuleEvaluationError
)

__version__ = "0.1.0"

__all__ = [
        'Schema',
    'load_schema',
    
        'TypeRegistry', 
    'register_builtin_types',
    
        'AminoError',
    'SchemaParseError', 
    'RuleParseError',
    'TypeValidationError',
    'RuleEvaluationError'
]
