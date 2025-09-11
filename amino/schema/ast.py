"""Schema AST definitions."""

import dataclasses
from typing import Any

from .types import SchemaType


@dataclasses.dataclass
class FieldDefinition:
    """Represents a field definition in the schema."""
    name: str
    field_type: SchemaType
    type_name: str = ""  # Original type name for custom types
    element_types: list[str] = dataclasses.field(default_factory=list)  # For list[type] or list[type|type]
    constraints: dict[str, Any] = dataclasses.field(default_factory=dict)
    optional: bool = False


@dataclasses.dataclass
class StructDefinition:
    """Represents a struct definition in the schema."""
    name: str
    fields: list[FieldDefinition]


@dataclasses.dataclass
class FunctionDefinition:
    """Represents a function declaration in the schema."""
    name: str
    input_types: list[SchemaType]
    output_type: SchemaType
    default_args: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class SchemaAST:
    """Root schema abstract syntax tree."""
    fields: list[FieldDefinition] = dataclasses.field(default_factory=list)
    structs: list[StructDefinition] = dataclasses.field(default_factory=list)
    functions: list[FunctionDefinition] = dataclasses.field(default_factory=list)
    constants: dict[str, Any] = dataclasses.field(default_factory=dict)
