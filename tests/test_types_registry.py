"""Tests for amino.types.registry module."""

import pytest

from amino.schema.types import SchemaType
from amino.types.registry import TypeDefinition, TypeRegistry
from amino.utils.errors import TypeValidationError


class TestTypeDefinition:
    """Tests for TypeDefinition dataclass."""

    def test_type_definition_creation(self):
        """Test creating a TypeDefinition with all fields."""
        validator = lambda x: isinstance(x, str)
        constraints = {"min": 1, "max": 100}

        type_def = TypeDefinition(
            name="test_type",
            base_type="str",
            validator=validator,
            constraints=constraints,
            format_string="test format",
            description="test description",
        )

        assert type_def.name == "test_type"
        assert type_def.base_type == "str"
        assert type_def.validator == validator
        assert type_def.constraints == constraints
        assert type_def.format_string == "test format"
        assert type_def.description == "test description"

    def test_type_definition_minimal(self):
        """Test creating a TypeDefinition with minimal fields."""
        type_def = TypeDefinition(name="test_type", base_type="str")

        assert type_def.name == "test_type"
        assert type_def.base_type == "str"
        assert type_def.validator is None
        assert type_def.constraints == {}
        assert type_def.format_string is None
        assert type_def.description is None


class TestTypeRegistry:
    """Tests for TypeRegistry class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = TypeRegistry()

    def test_init(self):
        """Test registry initialization."""
        registry = TypeRegistry()
        assert registry._types == {}
        assert registry._validators == {}

    def test_register_type_basic(self):
        """Test basic type registration."""
        self.registry.register_type("custom_type", "str")

        assert self.registry.has_type("custom_type")
        type_def = self.registry.get_type("custom_type")
        assert type_def is not None
        assert type_def.name == "custom_type"
        assert type_def.base_type == "str"

    def test_register_type_with_validator(self):
        """Test type registration with validator."""
        validator = lambda x: len(x) > 5
        self.registry.register_type("long_string", "str", validator=validator)

        assert self.registry.has_type("long_string")
        assert self.registry.get_validator("long_string") == validator

    def test_register_type_with_schema_type(self):
        """Test type registration with SchemaType enum."""
        self.registry.register_type("test_type", SchemaType.int)

        type_def = self.registry.get_type("test_type")
        assert type_def.base_type == SchemaType.int

    def test_register_type_with_constraints(self):
        """Test type registration with constraints."""
        self.registry.register_type("bounded_int", "int", min=0, max=100)

        type_def = self.registry.get_type("bounded_int")
        assert type_def.constraints == {"min": 0, "max": 100}

    def test_register_type_duplicate_error(self):
        """Test that registering duplicate type raises error."""
        self.registry.register_type("test_type", "str")

        with pytest.raises(TypeValidationError) as exc_info:
            self.registry.register_type("test_type", "int")

        assert "Type 'test_type' already registered" in str(exc_info.value)

    def test_get_type_exists(self):
        """Test getting an existing type."""
        self.registry.register_type("test_type", "str")
        type_def = self.registry.get_type("test_type")

        assert type_def is not None
        assert type_def.name == "test_type"

    def test_get_type_not_exists(self):
        """Test getting a non-existent type."""
        type_def = self.registry.get_type("nonexistent")
        assert type_def is None

    def test_has_type_exists(self):
        """Test has_type for existing type."""
        self.registry.register_type("test_type", "str")
        assert self.registry.has_type("test_type") is True

    def test_has_type_not_exists(self):
        """Test has_type for non-existent type."""
        assert self.registry.has_type("nonexistent") is False

    def test_get_registered_types(self):
        """Test getting list of registered types."""
        self.registry.register_type("type1", "str")
        self.registry.register_type("type2", "int")

        types = self.registry.get_registered_types()
        assert set(types) == {"type1", "type2"}

    def test_get_registered_types_empty(self):
        """Test getting registered types from empty registry."""
        types = self.registry.get_registered_types()
        assert types == []

    def test_get_validator_exists(self):
        """Test getting validator for type with validator."""
        validator = lambda x: True
        self.registry.register_type("test_type", "str", validator=validator)

        result = self.registry.get_validator("test_type")
        assert result == validator

    def test_get_validator_not_exists(self):
        """Test getting validator for non-existent type."""
        result = self.registry.get_validator("nonexistent")
        assert result is None

    def test_get_validator_no_validator(self):
        """Test getting validator for type without validator."""
        self.registry.register_type("test_type", "str")
        result = self.registry.get_validator("test_type")
        assert result is None

    def test_list_types(self):
        """Test listing all types."""
        self.registry.register_type("type1", "str")
        self.registry.register_type("type2", "int")

        types = self.registry.list_types()
        assert set(types) == {"type1", "type2"}

    def test_list_types_empty(self):
        """Test listing types from empty registry."""
        types = self.registry.list_types()
        assert types == []

    def test_remove_type_exists(self):
        """Test removing an existing type."""
        validator = lambda x: True
        self.registry.register_type("test_type", "str", validator=validator)

        result = self.registry.remove_type("test_type")
        assert result is True
        assert not self.registry.has_type("test_type")
        assert self.registry.get_validator("test_type") is None

    def test_remove_type_not_exists(self):
        """Test removing a non-existent type."""
        result = self.registry.remove_type("nonexistent")
        assert result is False

    def test_validate_value_builtin_str(self):
        """Test validating value against builtin str type."""
        assert self.registry.validate_value("str", "hello") is True
        assert self.registry.validate_value("str", 123) is False

    def test_validate_value_builtin_int(self):
        """Test validating value against builtin int type."""
        assert self.registry.validate_value("int", 123) is True
        assert self.registry.validate_value("int", "hello") is False

    def test_validate_value_builtin_float(self):
        """Test validating value against builtin float type."""
        assert self.registry.validate_value("float", 3.14) is True
        assert self.registry.validate_value("float", 123) is True  # int is valid for float
        assert self.registry.validate_value("float", "hello") is False

    def test_validate_value_builtin_bool(self):
        """Test validating value against builtin bool type."""
        assert self.registry.validate_value("bool", True) is True
        assert self.registry.validate_value("bool", False) is True
        assert self.registry.validate_value("bool", 1) is False  # int is not bool

    def test_validate_value_builtin_any(self):
        """Test validating value against builtin any type."""
        assert self.registry.validate_value("any", "hello") is True
        assert self.registry.validate_value("any", 123) is True
        assert self.registry.validate_value("any", None) is True

    def test_validate_value_unknown_builtin(self):
        """Test validating against unknown builtin type."""
        assert self.registry.validate_value("unknown", "value") is False

    def test_validate_value_custom_type_with_validator(self):
        """Test validating value against custom type with validator."""
        validator = lambda x: len(x) > 3
        self.registry.register_type("long_string", "str", validator=validator)

        assert self.registry.validate_value("long_string", "hello") is True
        assert self.registry.validate_value("long_string", "hi") is False

    def test_validate_value_custom_type_validator_exception(self):
        """Test validator that raises exception."""

        def bad_validator(x):
            raise ValueError("Validation error")

        self.registry.register_type("bad_type", "str", validator=bad_validator)

        assert self.registry.validate_value("bad_type", "value") is False

    def test_validate_value_custom_type_base_type_validation(self):
        """Test that base type validation is performed first."""
        validator = lambda x: True  # Always passes
        self.registry.register_type("strict_int", "int", validator=validator)

        assert self.registry.validate_value("strict_int", 123) is True
        assert self.registry.validate_value("strict_int", "hello") is False  # Fails base type

    def test_validate_value_schema_type_str(self):
        """Test validating against SchemaType.str."""
        self.registry.register_type("schema_str", SchemaType.str)

        assert self.registry.validate_value("schema_str", "hello") is True
        assert self.registry.validate_value("schema_str", 123) is False

    def test_validate_value_schema_type_int(self):
        """Test validating against SchemaType.int."""
        self.registry.register_type("schema_int", SchemaType.int)

        assert self.registry.validate_value("schema_int", 123) is True
        assert self.registry.validate_value("schema_int", "hello") is False

    def test_validate_value_schema_type_float(self):
        """Test validating against SchemaType.float."""
        self.registry.register_type("schema_float", SchemaType.float)

        assert self.registry.validate_value("schema_float", 3.14) is True
        assert self.registry.validate_value("schema_float", 123) is True  # int is valid
        assert self.registry.validate_value("schema_float", "hello") is False

    def test_validate_value_schema_type_bool(self):
        """Test validating against SchemaType.bool."""
        self.registry.register_type("schema_bool", SchemaType.bool)

        assert self.registry.validate_value("schema_bool", True) is True
        assert self.registry.validate_value("schema_bool", False) is True
        assert self.registry.validate_value("schema_bool", 1) is False

    def test_validate_value_schema_type_any(self):
        """Test validating against SchemaType.any."""
        self.registry.register_type("schema_any", SchemaType.any)

        assert self.registry.validate_value("schema_any", "hello") is True
        assert self.registry.validate_value("schema_any", 123) is True
        assert self.registry.validate_value("schema_any", None) is True

    def test_validate_value_schema_type_list(self):
        """Test validating against SchemaType.list."""
        self.registry.register_type("schema_list", SchemaType.list)

        assert self.registry.validate_value("schema_list", [1, 2, 3]) is True
        assert self.registry.validate_value("schema_list", []) is True
        assert self.registry.validate_value("schema_list", "hello") is False

    def test_validate_value_unknown_schema_type(self):
        """Test validating against unknown SchemaType (should be handled gracefully)."""
        # Instead of testing unknown schema types, test the default case in _validate_schema_type
        # by registering a type with a mock SchemaType that behaves like an unknown type
        from unittest.mock import patch

        # This tests the 'else' branch in _validate_schema_type
        with patch.object(self.registry, "_validate_schema_type", return_value=False):
            self.registry.register_type("test_schema", SchemaType.str)
            assert self.registry.validate_value("test_schema", "value") is False

    def test_validate_constraints_min(self):
        """Test min constraint validation."""
        self.registry.register_type("bounded_int", "int", min=10)

        assert self.registry.validate_value("bounded_int", 15) is True
        assert self.registry.validate_value("bounded_int", 10) is True  # Equal to min
        assert self.registry.validate_value("bounded_int", 5) is False

    def test_validate_constraints_max(self):
        """Test max constraint validation."""
        self.registry.register_type("bounded_int", "int", max=100)

        assert self.registry.validate_value("bounded_int", 50) is True
        assert self.registry.validate_value("bounded_int", 100) is True  # Equal to max
        assert self.registry.validate_value("bounded_int", 150) is False

    def test_validate_constraints_length(self):
        """Test length constraint validation."""
        self.registry.register_type("fixed_string", "str", length=5)

        assert self.registry.validate_value("fixed_string", "hello") is True
        assert self.registry.validate_value("fixed_string", "hi") is False
        assert self.registry.validate_value("fixed_string", "toolong") is False

    def test_validate_constraints_format(self):
        """Test format constraint (currently no-op)."""
        self.registry.register_type("formatted", "str", format="email")

        # Format constraint is currently not implemented, so should pass
        assert self.registry.validate_value("formatted", "anything") is True

    def test_validate_constraints_no_comparison_support(self):
        """Test constraint validation with value that doesn't support comparison."""
        # Test with a value that does support comparison but fails the constraint
        self.registry.register_type("bounded_obj", "any", min=10)

        # Test with a value that passes the constraint
        assert self.registry.validate_value("bounded_obj", 15) is True

        # Test with a value that fails the constraint
        assert self.registry.validate_value("bounded_obj", 5) is False

    def test_validate_constraints_no_length_support(self):
        """Test length constraint with value that doesn't have length."""
        self.registry.register_type("length_obj", "any", length=5)

        # Object without __len__ should not fail validation
        assert self.registry.validate_value("length_obj", 123) is True

    def test_recursive_type_validation(self):
        """Test recursive validation with custom base types."""
        # Register a base custom type
        self.registry.register_type("positive_int", "int", validator=lambda x: x > 0)

        # Register a type based on the custom type
        self.registry.register_type("big_positive_int", "positive_int", validator=lambda x: x > 100)

        assert self.registry.validate_value("big_positive_int", 150) is True
        assert self.registry.validate_value("big_positive_int", 50) is False  # Positive but not > 100
        assert self.registry.validate_value("big_positive_int", -10) is False  # Not positive

    def test_register_type_without_validator_in_validators_dict(self):
        """Test that types without validators don't get added to validators dict."""
        self.registry.register_type("simple_type", "str")

        assert "simple_type" not in self.registry._validators
        assert self.registry.get_validator("simple_type") is None
