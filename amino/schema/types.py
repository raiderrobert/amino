"""Schema type definitions."""

import enum


class SchemaType(enum.Enum):
    """Built-in schema types."""

    str = "Str"
    int = "Int"
    float = "Float"
    bool = "Bool"
    decimal = "Decimal"
    any = "Any"

    # Complex types
    list = "List"
    struct = "Struct"

    # Special types
    custom = "custom"


def parse_type(type_str: str, strict: bool = False, known_custom_types: set | None = None) -> SchemaType:
    """Parse a type string to SchemaType enum.

    Args:
        type_str: The type string to parse
        strict: If True, raise error for unknown types instead of treating as custom
        known_custom_types: Set of known custom type names for validation
    """
    type_map = {
        # Capitalized types (new standard)
        "Str": SchemaType.str,
        "Int": SchemaType.int,
        "Float": SchemaType.float,
        "Bool": SchemaType.bool,
        "Decimal": SchemaType.decimal,
        "Any": SchemaType.any,
        "List": SchemaType.list,
        "Struct": SchemaType.struct,
        # Lowercase types (backward compatibility)
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

    # Handle list types like List[Int] or list[int] (backward compatibility)
    if (type_str.startswith("List[") or type_str.startswith("list[")) and type_str.endswith("]"):
        return SchemaType.list

    # Check if it's a known custom type
    if known_custom_types and type_str in known_custom_types:
        return SchemaType.custom

    # In strict mode, reject unknown types
    if strict and not (known_custom_types and type_str in known_custom_types):
        from ..utils.errors import SchemaParseError

        raise SchemaParseError(f"Unknown type: {type_str}. Use strict=False to allow custom types.")

    # Custom type (default behavior)
    return SchemaType.custom
