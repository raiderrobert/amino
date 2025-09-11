"""Test type system functionality."""

import pytest

from amino.schema.parser import parse_schema
from amino.types import TypeRegistry, TypeValidator, register_builtin_types
from amino.utils.errors import TypeValidationError


@pytest.mark.parametrize(
    "type_name,base_type,value,expected_valid,has_validator",
    [
        ("positive_int", "int", 5, True, True),
        ("positive_int", "int", -5, False, True),
        ("positive_int", "int", "5", False, True),
        ("email", "str", "user@example.com", True, False),
        ("email", "str", "invalid-email", False, False),
        ("email", "str", "user@", False, False),
        ("credit_score", "int", 750, True, False),
        ("credit_score", "int", 300, True, False),
        ("credit_score", "int", 850, True, False),
        ("credit_score", "int", 299, False, False),
        ("credit_score", "int", 851, False, False),
        ("currency", "float", 100, True, False),
        ("currency", "float", 100.50, True, False),
        ("currency", "float", 0, True, False),
        ("currency", "float", -10, False, False),
        ("currency", "float", 10.123, False, False),
    ]
)
def test_type_validation(type_name, base_type, value, expected_valid, has_validator, type_registry, populated_type_registry, custom_type_registry):
    """Test type validation for various types."""
    if has_validator:
        registry = custom_type_registry
    else:
        registry = populated_type_registry

    assert registry.has_type(type_name)
    assert registry.validate_value(type_name, value) is expected_valid


@pytest.mark.parametrize(
    "type_name,base_type,constraints,value,expected_valid",
    [
        ("limited_int", "int", {"min": 10, "max": 100}, 50, True),
        ("limited_int", "int", {"min": 10, "max": 100}, 10, True),
        ("limited_int", "int", {"min": 10, "max": 100}, 100, True),
        ("limited_int", "int", {"min": 10, "max": 100}, 5, False),
        ("limited_int", "int", {"min": 10, "max": 100}, 150, False),
    ]
)
def test_type_constraints(type_name, base_type, constraints, value, expected_valid, type_registry):
    """Test type constraints validation."""
    type_registry.register_type(type_name, base_type, **constraints)

    assert type_registry.validate_value(type_name, value) is expected_valid


class TestTypeRegistry:
    """Test the TypeRegistry functionality for non-parametrizable tests."""

    def test_builtin_types_registration(self):
        """Test registration of built-in types."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        assert registry.has_type("email")
        assert registry.has_type("credit_score")
        assert registry.has_type("currency")

    def test_duplicate_registration_error(self):
        """Test error on duplicate type registration."""
        registry = TypeRegistry()
        registry.register_type("custom", "int")

        with pytest.raises(TypeValidationError):
            registry.register_type("custom", "str")

    def test_type_removal(self):
        """Test type removal from registry."""
        registry = TypeRegistry()
        registry.register_type("temp_type", "int")

        assert registry.has_type("temp_type")
        assert registry.remove_type("temp_type") is True
        assert not registry.has_type("temp_type")
        assert registry.remove_type("nonexistent") is False


@pytest.mark.parametrize(
    "schema_content,data,expected_valid,expected_error_count,error_field,error_contains",
    [
        ("name: str\nage: int", {"name": "John", "age": 25}, True, 0, None, None),

        ("name: str\nage: int", {"name": "John"}, False, 1, "age", "missing"),

        ("name: str\nage: int", {"name": "John", "age": "25"}, False, 1, "age", None),

        ("name: str\nage: int?", {"name": "John", "age": 25}, True, 0, None, None),

        ("name: str\nage: int?", {"name": "John"}, True, 0, None, None),

        ("name: str\nage: int?", {"name": "John", "age": None}, True, 0, None, None),
    ]
)
def test_basic_validation(schema_content, data, expected_valid, expected_error_count, error_field, error_contains):
    """Test basic data validation scenarios."""
    schema_ast = parse_schema(schema_content)
    validator = TypeValidator(schema_ast)

    result = validator.validate_data(data)

    assert result.valid is expected_valid
    assert len(result.errors) == expected_error_count

    if error_field:
        assert error_field in result.errors[0].field
    if error_contains:
        assert error_contains in result.errors[0].message.lower()


@pytest.mark.parametrize(
    "schema_content,data,expected_valid,error_contains",
    [
        ("age: int {min: 18, max: 120}", {"age": 25}, True, None),

        ("age: int {min: 18, max: 120}", {"age": 16}, False, "minimum"),

        ("age: int {min: 18, max: 120}", {"age": 150}, False, "maximum"),

        ("email: str {format: email}", {"email": "user@example.com"}, True, None),

        ("email: str {format: email}", {"email": "invalid-email"}, False, "email"),
    ]
)
def test_constraint_validation(schema_content, data, expected_valid, error_contains):
    """Test validation with field constraints."""
    schema_ast = parse_schema(schema_content)
    validator = TypeValidator(schema_ast)

    result = validator.validate_data(data)

    assert result.valid is expected_valid
    if error_contains:
        assert error_contains in result.errors[0].message.lower()


class TestTypeValidator:
    """Test the TypeValidator functionality for non-parametrizable tests."""

    def test_custom_type_validation(self):
        """Test validation with custom types."""
        registry = TypeRegistry()
        registry.register_type("positive_int", "int",
                              validator=lambda x: isinstance(x, int) and x > 0)

        schema_ast = parse_schema("score: positive_int")
        validator = TypeValidator(schema_ast, registry)

        result = validator.validate_data({"score": 100})
        assert result.valid is True

        result = validator.validate_data({"score": -10})
        assert result.valid is False


def test_list_element_validation():
    """Test validation of list element types."""
    schema_content = """
    numbers: list[int]
    mixed: list[int|str]
    """

    ast = parse_schema(schema_content)
    validator = TypeValidator(ast)

    valid_data = {"numbers": [1, 2, 3], "mixed": [1, "hello", 2, "world"]}
    result = validator.validate_data(valid_data)
    assert result.valid is True

    invalid_data = {"numbers": [1, "hello", 3], "mixed": [1, 2, 3]}
    result = validator.validate_data(invalid_data)
    assert result.valid is False
    assert len(result.errors) == 1
    assert "Element at index 1" in result.errors[0].message
    assert "does not match allowed types [int]" in result.errors[0].message
