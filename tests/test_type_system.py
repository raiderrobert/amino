"""Test type system functionality."""

import pytest
from amino.types import TypeRegistry, register_builtin_types, ValidationResult, TypeValidator
from amino.schema.parser import parse_schema
from amino.utils.errors import TypeValidationError


class TestTypeRegistry:
    """Test the TypeRegistry functionality."""

    def test_basic_type_registration(self):
        """Test basic custom type registration."""
        registry = TypeRegistry()
        
        def validate_positive(value):
            return isinstance(value, int) and value > 0
        
        registry.register_type("positive_int", "int", validator=validate_positive)
        
        assert registry.has_type("positive_int")
        assert registry.validate_value("positive_int", 5) is True
        assert registry.validate_value("positive_int", -5) is False
        assert registry.validate_value("positive_int", "5") is False

    def test_builtin_types_registration(self):
        """Test registration of built-in types."""
        registry = TypeRegistry()
        register_builtin_types(registry)
        
        # Test some built-in types
        assert registry.has_type("email")
        assert registry.has_type("credit_score")
        assert registry.has_type("currency")

    def test_email_validation(self):
        """Test email type validation."""
        registry = TypeRegistry()
        register_builtin_types(registry)
        
        assert registry.validate_value("email", "user@example.com") is True
        assert registry.validate_value("email", "invalid-email") is False
        assert registry.validate_value("email", "user@") is False

    def test_credit_score_validation(self):
        """Test credit score validation.""" 
        registry = TypeRegistry()
        register_builtin_types(registry)
        
        assert registry.validate_value("credit_score", 750) is True
        assert registry.validate_value("credit_score", 300) is True
        assert registry.validate_value("credit_score", 850) is True
        assert registry.validate_value("credit_score", 299) is False
        assert registry.validate_value("credit_score", 851) is False

    def test_currency_validation(self):
        """Test currency validation."""
        registry = TypeRegistry()
        register_builtin_types(registry)
        
        assert registry.validate_value("currency", 100) is True
        assert registry.validate_value("currency", 100.50) is True
        assert registry.validate_value("currency", 0) is True
        assert registry.validate_value("currency", -10) is False
        assert registry.validate_value("currency", 10.123) is False  # Too many decimals

    def test_type_constraints(self):
        """Test type constraints validation."""
        registry = TypeRegistry()
        registry.register_type("limited_int", "int", min=10, max=100)
        
        assert registry.validate_value("limited_int", 50) is True
        assert registry.validate_value("limited_int", 10) is True
        assert registry.validate_value("limited_int", 100) is True
        assert registry.validate_value("limited_int", 5) is False
        assert registry.validate_value("limited_int", 150) is False

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


class TestTypeValidator:
    """Test the TypeValidator functionality."""

    def test_basic_validation(self):
        """Test basic data validation."""
        schema_ast = parse_schema("name: str\nage: int")
        validator = TypeValidator(schema_ast)
        
        data = {"name": "John", "age": 25}
        result = validator.validate_data(data)
        
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_required_field(self):
        """Test validation with missing required field."""
        schema_ast = parse_schema("name: str\nage: int")
        validator = TypeValidator(schema_ast)
        
        data = {"name": "John"}  # Missing age
        result = validator.validate_data(data)
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert "age" in result.errors[0].field
        assert "missing" in result.errors[0].message.lower()

    def test_optional_field_validation(self):
        """Test validation with optional fields."""
        schema_ast = parse_schema("name: str\nage: int?")
        validator = TypeValidator(schema_ast)
        
        # With optional field
        data = {"name": "John", "age": 25}
        result = validator.validate_data(data)
        assert result.valid is True
        
        # Without optional field
        data = {"name": "John"}
        result = validator.validate_data(data)
        assert result.valid is True
        
        # With None value for optional field
        data = {"name": "John", "age": None}
        result = validator.validate_data(data)
        assert result.valid is True

    def test_wrong_type_validation(self):
        """Test validation with wrong data types."""
        schema_ast = parse_schema("name: str\nage: int")
        validator = TypeValidator(schema_ast)
        
        data = {"name": "John", "age": "25"}  # age should be int
        result = validator.validate_data(data)
        
        assert result.valid is False
        assert len(result.errors) == 1
        assert "age" in result.errors[0].field

    def test_constraint_validation(self):
        """Test validation with field constraints."""
        schema_ast = parse_schema("age: int {min: 18, max: 120}")
        validator = TypeValidator(schema_ast)
        
        # Valid age
        result = validator.validate_data({"age": 25})
        assert result.valid is True
        
        # Too young
        result = validator.validate_data({"age": 16})
        assert result.valid is False
        assert "minimum" in result.errors[0].message.lower()
        
        # Too old
        result = validator.validate_data({"age": 150})
        assert result.valid is False
        assert "maximum" in result.errors[0].message.lower()

    def test_custom_type_validation(self):
        """Test validation with custom types."""
        registry = TypeRegistry()
        registry.register_type("positive_int", "int", 
                              validator=lambda x: isinstance(x, int) and x > 0)
        
        schema_ast = parse_schema("score: positive_int")
        validator = TypeValidator(schema_ast, registry)
        
        # Valid positive integer
        result = validator.validate_data({"score": 100})
        assert result.valid is True
        
        # Invalid (negative)
        result = validator.validate_data({"score": -10})
        assert result.valid is False

    def test_format_validation(self):
        """Test format constraint validation."""
        schema_ast = parse_schema("email: str {format: email}")
        validator = TypeValidator(schema_ast)
        
        # Valid email
        result = validator.validate_data({"email": "user@example.com"})
        assert result.valid is True
        
        # Invalid email
        result = validator.validate_data({"email": "invalid-email"})
        assert result.valid is False
        assert "email" in result.errors[0].message.lower()