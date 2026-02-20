import pytest
from amino.schema.parser import parse_schema
from amino.schema.ast import SchemaType
from amino.errors import SchemaParseError

def test_primitive_field():
    ast = parse_schema("age: Int")
    assert ast.fields[0].name == "age"
    assert ast.fields[0].schema_type == SchemaType.INT

def test_optional_field():
    assert parse_schema("email: Str?").fields[0].optional is True

def test_list_field():
    f = parse_schema("tags: List[Str]").fields[0]
    assert f.schema_type == SchemaType.LIST
    assert f.element_types == ["Str"]

def test_union_list():
    f = parse_schema("vals: List[Int|Str]").fields[0]
    assert f.element_types == ["Int", "Str"]

def test_numeric_constraints():
    f = parse_schema("age: Int {min: 18, max: 120}").fields[0]
    assert f.constraints == {"min": 18, "max": 120}

def test_float_constraint():
    f = parse_schema("price: Float {min: 0.01}").fields[0]
    assert f.constraints["min"] == 0.01

def test_string_oneof_constraint():
    f = parse_schema("status: Str {oneOf: ['active', 'inactive']}").fields[0]
    assert f.constraints["oneOf"] == ["active", "inactive"]

def test_pattern_constraint():
    f = parse_schema("u: Str {pattern: '^[a-z]+$'}").fields[0]
    assert f.constraints["pattern"] == "^[a-z]+$"

def test_boolean_constraint():
    f = parse_schema("tags: List[Str] {unique: true}").fields[0]
    assert f.constraints["unique"] is True

def test_struct_definition():
    ast = parse_schema("struct Addr {\n  street: Str,\n  city: Str\n}")
    assert len(ast.structs) == 1
    assert len(ast.structs[0].fields) == 2

def test_struct_newline_separator():
    ast = parse_schema("struct Foo {\n  a: Int\n  b: Str\n}")
    assert len(ast.structs[0].fields) == 2

def test_function_definition():
    ast = parse_schema("check: (addr: Str) -> Bool")
    assert ast.functions[0].name == "check"
    assert ast.functions[0].return_type_name == "Bool"

def test_custom_type_field():
    f = parse_schema("ip: ipv4").fields[0]
    assert f.schema_type == SchemaType.CUSTOM
    assert f.type_name == "ipv4"

def test_comments_skipped():
    ast = parse_schema("# comment\nage: Int  # inline")
    assert len(ast.fields) == 1

def test_parse_error():
    with pytest.raises(SchemaParseError):
        parse_schema("age: @Int")
