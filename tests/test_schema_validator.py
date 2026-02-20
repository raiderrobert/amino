import pytest
from amino.schema.parser import parse_schema
from amino.schema.validator import SchemaValidator
from amino.errors import SchemaValidationError

def test_valid_passes():
    SchemaValidator(parse_schema("age: Int\nname: Str")).validate()

def test_duplicate_field_raises():
    with pytest.raises(SchemaValidationError, match="Duplicate"):
        SchemaValidator(parse_schema("age: Int\nage: Str")).validate()

def test_unknown_type_raises():
    with pytest.raises(SchemaValidationError, match="Unknown type"):
        SchemaValidator(parse_schema("addr: UnknownStruct")).validate()

def test_known_custom_type_passes():
    SchemaValidator(parse_schema("ip: ipv4"), known_custom_types={"ipv4"}).validate()

def test_circular_struct_raises():
    ast = parse_schema("struct A { b: B }\nstruct B { a: A }")
    with pytest.raises(SchemaValidationError, match="Circular"):
        SchemaValidator(ast).validate()

def test_valid_nested_struct_passes():
    ast = parse_schema("struct Addr { city: Str }\nstruct User { addr: Addr }")
    SchemaValidator(ast).validate()

def test_duplicate_struct_field_raises():
    with pytest.raises(SchemaValidationError, match="Duplicate"):
        SchemaValidator(parse_schema("struct Foo { x: Int, x: Str }")).validate()
