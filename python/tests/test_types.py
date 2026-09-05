import pytest
from amino.types.registry import TypeRegistry
from amino.types.builtin import register_builtin_types

def test_register_custom_type():
    reg = TypeRegistry()
    reg.register_type("ipv4", base="Str", validator=lambda v: isinstance(v, str))
    assert reg.has_type("ipv4")

def test_base_type_lookup():
    reg = TypeRegistry()
    reg.register_type("ipv4", base="Str", validator=lambda v: True)
    assert reg.get_base("ipv4") == "Str"

def test_validate_valid_value():
    reg = TypeRegistry()
    reg.register_type("posint", base="Int", validator=lambda v: v > 0)
    assert reg.validate("posint", 5) is True

def test_validate_invalid_value():
    reg = TypeRegistry()
    reg.register_type("posint", base="Int", validator=lambda v: v > 0)
    assert reg.validate("posint", -1) is False

def test_duplicate_registration_raises():
    from amino.errors import SchemaValidationError
    reg = TypeRegistry()
    reg.register_type("t", base="Str", validator=lambda v: True)
    with pytest.raises(Exception):
        reg.register_type("t", base="Str", validator=lambda v: True)

def test_builtin_types_registered():
    reg = TypeRegistry()
    register_builtin_types(reg)
    for name in ["ipv4", "ipv6", "cidr", "email", "uuid"]:
        assert reg.has_type(name), f"missing builtin type: {name}"

def test_builtin_ipv4_validates():
    reg = TypeRegistry()
    register_builtin_types(reg)
    assert reg.validate("ipv4", "192.168.1.1") is True
    assert reg.validate("ipv4", "not-an-ip") is False

def test_builtin_cidr_validates():
    reg = TypeRegistry()
    register_builtin_types(reg)
    assert reg.validate("cidr", "10.0.0.0/8") is True
    assert reg.validate("cidr", "10.0.0.0") is False
