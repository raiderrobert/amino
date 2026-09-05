# amino/schema/ast.py
import dataclasses
import enum
from typing import Any


class SchemaType(enum.Enum):
    INT = "Int"
    FLOAT = "Float"
    STR = "Str"
    BOOL = "Bool"
    LIST = "List"
    STRUCT = "struct"
    CUSTOM = "custom"


@dataclasses.dataclass
class FieldDefinition:
    name: str
    schema_type: SchemaType
    type_name: str
    element_types: list[str] = dataclasses.field(default_factory=list)
    constraints: dict[str, Any] = dataclasses.field(default_factory=dict)
    optional: bool = False


@dataclasses.dataclass
class StructDefinition:
    name: str
    fields: list[FieldDefinition]


@dataclasses.dataclass
class FunctionParameter:
    name: str
    type_name: str


@dataclasses.dataclass
class FunctionDefinition:
    name: str
    parameters: list[FunctionParameter]
    return_type_name: str


@dataclasses.dataclass
class SchemaAST:
    fields: list[FieldDefinition] = dataclasses.field(default_factory=list)
    structs: list[StructDefinition] = dataclasses.field(default_factory=list)
    functions: list[FunctionDefinition] = dataclasses.field(default_factory=list)
