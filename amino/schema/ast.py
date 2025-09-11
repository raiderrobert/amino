"""Schema AST definitions."""

import dataclasses
from typing import List, Dict, Any
from .types import SchemaType


@dataclasses.dataclass
class FieldDefinition:
    """Represents a field definition in the schema."""
    name: str
    field_type: SchemaType
    type_name: str = ""  # Original type name for custom types
    element_types: List[str] = dataclasses.field(default_factory=list)  # For list[type] or list[type|type]
    constraints: Dict[str, Any] = dataclasses.field(default_factory=dict)
    optional: bool = False


@dataclasses.dataclass 
class StructDefinition:
    """Represents a struct definition in the schema."""
    name: str
    fields: List[FieldDefinition]


@dataclasses.dataclass
class FunctionDefinition:
    """Represents a function declaration in the schema."""
    name: str
    input_types: List[SchemaType]
    output_type: SchemaType
    default_args: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class SchemaAST:
    """Root schema abstract syntax tree."""
    fields: List[FieldDefinition] = dataclasses.field(default_factory=list)
    structs: List[StructDefinition] = dataclasses.field(default_factory=list)
    functions: List[FunctionDefinition] = dataclasses.field(default_factory=list)
    constants: Dict[str, Any] = dataclasses.field(default_factory=dict)