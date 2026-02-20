from amino.schema.ast import SchemaType
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry


def _reg(src: str, custom: set[str] | None = None) -> SchemaRegistry:
    return SchemaRegistry(parse_schema(src), known_custom_types=custom or set())

def test_primitive_field_lookup():
    assert _reg("age: Int").get_field("age").schema_type == SchemaType.INT

def test_missing_field_returns_none():
    assert _reg("age: Int").get_field("nope") is None

def test_dot_notation():
    f = _reg("struct Addr { city: Str }\naddr: Addr").get_field("addr.city")
    assert f.schema_type == SchemaType.STR

def test_deep_dot_notation():
    src = "struct I { x: Int }\nstruct O { inner: I }\nouter: O"
    f = _reg(src).get_field("outer.inner.x")
    assert f is not None and f.schema_type == SchemaType.INT

def test_export_roundtrip():
    exported = _reg("age: Int\nname: Str?").export_schema()
    assert "age: Int" in exported
    assert "name: Str?" in exported

def test_known_type_names_includes_custom():
    assert "ipv4" in _reg("ip: ipv4", custom={"ipv4"}).known_type_names()

def test_export_struct_with_constraint():
    exported = _reg("struct Foo { age: Int {min: 0} }\nx: Foo").export_schema()
    assert "min" in exported
