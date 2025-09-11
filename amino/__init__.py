"""Amino - Schema-first classification rules engine."""

from .core import Schema, load_schema
from .types import TypeRegistry, register_builtin_types
from .utils.errors import (
    AminoError,
    RuleEvaluationError,
    RuleParseError,
    SchemaParseError,
    TypeValidationError,
)

__version__ = "0.1.0"

__all__ = [
    'AminoError',
    'RuleEvaluationError',
    'RuleParseError',
    'Schema',
    'SchemaParseError',
    'TypeRegistry',
    'TypeValidationError',
    'load_schema',
    'register_builtin_types'
]
