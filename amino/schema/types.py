"""Schema type definitions."""

import enum
from typing import Any, List, Union, Optional


class SchemaType(enum.Enum):
    """Built-in schema types."""
    str = "str"
    int = "int"
    float = "float" 
    bool = "bool"
    decimal = "decimal"
    any = "any"
    
    # Complex types
    list = "list"
    struct = "struct"
    
    # Special types
    custom = "custom"


def parse_type(type_str: str) -> SchemaType:
    """Parse a type string to SchemaType enum."""
    type_map = {
        "str": SchemaType.str,
        "int": SchemaType.int,
        "float": SchemaType.float,
        "bool": SchemaType.bool,
        "decimal": SchemaType.decimal,
        "any": SchemaType.any,
        "list": SchemaType.list,
        "struct": SchemaType.struct,
    }
    
    if type_str in type_map:
        return type_map[type_str]
    
    # Handle list types like list[int]
    if type_str.startswith("list[") and type_str.endswith("]"):
        return SchemaType.list
    
    # Custom type
    return SchemaType.custom