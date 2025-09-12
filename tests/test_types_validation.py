"""Tests for amino.types.validation module."""

from amino.schema.ast import FieldDefinition, SchemaAST, StructDefinition
from amino.schema.types import SchemaType
from amino.types.registry import TypeRegistry
from amino.types.validation import TypeValidator, ValidationError, ValidationResult


class TestValidationError:
    """Tests for ValidationError dataclass."""

    def test_validation_error_creation(self):
        """Test creating a ValidationError with all fields."""
        error = ValidationError(field="test_field", message="Test message", value=123)

        assert error.field == "test_field"
        assert error.message == "Test message"
        assert error.value == 123

    def test_validation_error_without_value(self):
        """Test creating a ValidationError without value."""
        error = ValidationError(field="test_field", message="Test message")

        assert error.field == "test_field"
        assert error.message == "Test message"
        assert error.value is None


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_valid(self):
        """Test creating a valid ValidationResult."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []

    def test_validation_result_invalid(self):
        """Test creating an invalid ValidationResult."""
        errors = [ValidationError("field1", "error1")]
        result = ValidationResult(valid=False, errors=errors)

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "field1"

    def test_add_error(self):
        """Test adding an error to ValidationResult."""
        result = ValidationResult(valid=True)

        result.add_error("test_field", "Test error", 123)

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "test_field"
        assert result.errors[0].message == "Test error"
        assert result.errors[0].value == 123

    def test_add_error_without_value(self):
        """Test adding an error without value."""
        result = ValidationResult(valid=True)

        result.add_error("test_field", "Test error")

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].value is None

    def test_multiple_errors(self):
        """Test adding multiple errors."""
        result = ValidationResult(valid=True)

        result.add_error("field1", "error1")
        result.add_error("field2", "error2")

        assert result.valid is False
        assert len(result.errors) == 2


class TestTypeValidator:
    """Tests for TypeValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.schema_ast = SchemaAST(fields=[], structs=[], functions=[])
        self.type_registry = TypeRegistry()
        self.validator = TypeValidator(self.schema_ast, self.type_registry)

    def test_init_with_registry(self):
        """Test validator initialization with type registry."""
        validator = TypeValidator(self.schema_ast, self.type_registry)
        assert validator.schema_ast == self.schema_ast
        assert validator.type_registry == self.type_registry

    def test_init_without_registry(self):
        """Test validator initialization without type registry."""
        validator = TypeValidator(self.schema_ast)
        assert validator.schema_ast == self.schema_ast
        assert isinstance(validator.type_registry, TypeRegistry)

    def test_validate_data_empty_schema(self):
        """Test validating data against empty schema."""
        data = {"field1": "value1"}
        result = self.validator.validate_data(data)

        assert result.valid is True
        assert result.errors == []

    def test_validate_data_required_field_present(self):
        """Test validating data with required field present."""
        field_def = FieldDefinition("name", SchemaType.str, optional=False)
        self.schema_ast.fields = [field_def]

        data = {"name": "test"}
        result = self.validator.validate_data(data)

        assert result.valid is True
        assert result.errors == []

    def test_validate_data_required_field_missing(self):
        """Test validating data with required field missing."""
        field_def = FieldDefinition("name", SchemaType.str, optional=False)
        self.schema_ast.fields = [field_def]

        data = {}
        result = self.validator.validate_data(data)

        assert result.valid is False
        assert len(result.errors) == 1
        assert "Required field 'name' missing" in result.errors[0].message

    def test_validate_data_optional_field_missing(self):
        """Test validating data with optional field missing."""
        field_def = FieldDefinition("name", SchemaType.str, optional=True)
        self.schema_ast.fields = [field_def]

        data = {}
        result = self.validator.validate_data(data)

        assert result.valid is True
        assert result.errors == []

    def test_validate_data_optional_field_none(self):
        """Test validating data with optional field set to None."""
        field_def = FieldDefinition("name", SchemaType.str, optional=True)
        self.schema_ast.fields = [field_def]

        data = {"name": None}
        result = self.validator.validate_data(data)

        assert result.valid is True
        assert result.errors == []

    def test_validate_data_struct_valid(self):
        """Test validating data with valid struct."""
        struct_field = FieldDefinition("name", SchemaType.str, optional=False)
        struct_def = StructDefinition("person", [struct_field])
        self.schema_ast.structs = [struct_def]

        data = {"person": {"name": "John"}}
        result = self.validator.validate_data(data)

        assert result.valid is True
        assert result.errors == []

    def test_validate_data_struct_invalid_type(self):
        """Test validating data with struct as non-dict."""
        struct_field = FieldDefinition("name", SchemaType.str, optional=False)
        struct_def = StructDefinition("person", [struct_field])
        self.schema_ast.structs = [struct_def]

        data = {"person": "not a dict"}
        result = self.validator.validate_data(data)

        assert result.valid is False
        assert "Expected object for struct 'person'" in result.errors[0].message

    def test_validate_data_struct_missing_field(self):
        """Test validating struct with missing required field."""
        struct_field = FieldDefinition("name", SchemaType.str, optional=False)
        struct_def = StructDefinition("person", [struct_field])
        self.schema_ast.structs = [struct_def]

        data = {"person": {}}
        result = self.validator.validate_data(data)

        assert result.valid is False
        assert "Required field 'person.name' missing" in result.errors[0].message

    def test_validate_field_value_known_field(self):
        """Test validating a known field value."""
        field_def = FieldDefinition("name", SchemaType.str, optional=False)
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_field_value("name", "test")

        assert result.valid is True
        assert result.errors == []

    def test_validate_field_value_unknown_field(self):
        """Test validating an unknown field value."""
        result = self.validator.validate_field_value("unknown", "test")

        assert result.valid is False
        assert "Unknown field 'unknown'" in result.errors[0].message

    def test_validate_field_value_invalid_type(self):
        """Test validating field value with wrong type."""
        field_def = FieldDefinition("age", SchemaType.int, optional=False)
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_field_value("age", "not an int")

        assert result.valid is False
        assert "Expected Int for field 'age'" in result.errors[0].message

    def test_validate_list_type_valid(self):
        """Test validating valid list type."""
        field_def = FieldDefinition("items", SchemaType.list, optional=False)
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"items": [1, 2, 3]})

        assert result.valid is True

    def test_validate_list_type_invalid(self):
        """Test validating invalid list type."""
        field_def = FieldDefinition("items", SchemaType.list, optional=False)
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"items": "not a list"})

        assert result.valid is False
        assert "Expected List for field 'items'" in result.errors[0].message

    def test_validate_list_elements_valid(self):
        """Test validating list with valid elements."""
        field_def = FieldDefinition("items", SchemaType.list, optional=False, element_types=["Str"])
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"items": ["a", "b", "c"]})

        assert result.valid is True

    def test_validate_list_elements_invalid(self):
        """Test validating list with invalid elements."""
        field_def = FieldDefinition("items", SchemaType.list, optional=False, element_types=["Str"])
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"items": ["a", 123, "c"]})

        assert result.valid is False
        assert "Element at index 1 does not match allowed types [Str]" in result.errors[0].message

    def test_validate_list_elements_multiple_types(self):
        """Test validating list with multiple allowed element types."""
        field_def = FieldDefinition("items", SchemaType.list, optional=False, element_types=["Str", "Int"])
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"items": ["a", 123, "c"]})

        assert result.valid is True

    def test_validate_custom_type_valid(self):
        """Test validating custom type that's valid."""
        # Register custom type
        self.type_registry.register_type("positive_int", "Int", validator=lambda x: x > 0)

        field_def = FieldDefinition("score", SchemaType.custom, optional=False, type_name="positive_int")
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"score": 10})

        assert result.valid is True

    def test_validate_custom_type_invalid(self):
        """Test validating custom type that's invalid."""
        # Register custom type
        self.type_registry.register_type("positive_int", "Int", validator=lambda x: x > 0)

        field_def = FieldDefinition("score", SchemaType.custom, optional=False, type_name="positive_int")
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"score": -5})

        assert result.valid is False
        assert "Value does not match type 'positive_int'" in result.errors[0].message

    def test_validate_registered_builtin_type(self):
        """Test validating registered built-in type."""
        self.type_registry.register_type("email", "Str", validator=lambda x: "@" in x)

        # Create a custom field type
        field_def = FieldDefinition("contact", SchemaType.custom, optional=False, type_name="email")
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"contact": "not-email"})

        assert result.valid is False
        assert "Value does not match type 'email'" in result.errors[0].message

    def test_validate_builtin_types(self):
        """Test validating various built-in types."""
        test_cases = [
            ("Str", "hello", True),
            ("Str", 123, False),
            ("Int", 123, True),
            ("Int", "hello", False),
            ("Float", 3.14, True),
            ("Float", 123, True),  # int is valid for float
            ("Float", "hello", False),
            ("Bool", True, True),
            ("Bool", 1, False),  # int is not bool
            ("decimal", 3.14, True),
            ("decimal", 123, True),
            ("any", "anything", True),
        ]

        for type_name, value, should_be_valid in test_cases:
            # Map capitalized type names to lowercase enum attributes
            type_attr_map = {
                "Str": "str",
                "Int": "int",
                "Float": "float",
                "Bool": "bool",
                "decimal": "decimal",
                "any": "any",
            }
            schema_type = getattr(SchemaType, type_attr_map.get(type_name, type_name))
            field_def = FieldDefinition("test_field", schema_type, optional=False)
            self.schema_ast.fields = [field_def]

            result = self.validator.validate_data({"test_field": value})

            assert result.valid == should_be_valid, f"Failed for {type_name} with {value}"

    def test_validate_unknown_builtin_type(self):
        """Test validating unknown built-in type using custom type path."""
        # Create a field with a non-existent custom type
        field_def = FieldDefinition("test_field", SchemaType.custom, optional=False, type_name="unknown_type")
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"test_field": "value"})

        assert result.valid is False
        assert "Value does not match type 'unknown_type'" in result.errors[0].message

    def test_validate_constraints_min_valid(self):
        """Test min constraint validation - valid case."""
        field_def = FieldDefinition("age", SchemaType.int, optional=False, constraints={"min": 18})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"age": 25})

        assert result.valid is True

    def test_validate_constraints_min_invalid(self):
        """Test min constraint validation - invalid case."""
        field_def = FieldDefinition("age", SchemaType.int, optional=False, constraints={"min": 18})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"age": 15})

        assert result.valid is False
        assert "less than minimum 18" in result.errors[0].message

    def test_validate_constraints_max_valid(self):
        """Test max constraint validation - valid case."""
        field_def = FieldDefinition("score", SchemaType.int, optional=False, constraints={"max": 100})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"score": 95})

        assert result.valid is True

    def test_validate_constraints_max_invalid(self):
        """Test max constraint validation - invalid case."""
        field_def = FieldDefinition("score", SchemaType.int, optional=False, constraints={"max": 100})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"score": 150})

        assert result.valid is False
        assert "greater than maximum 100" in result.errors[0].message

    def test_validate_constraints_length_valid(self):
        """Test length constraint validation - valid case."""
        field_def = FieldDefinition("code", SchemaType.str, optional=False, constraints={"length": 5})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"code": "ABCDE"})

        assert result.valid is True

    def test_validate_constraints_length_invalid(self):
        """Test length constraint validation - invalid case."""
        field_def = FieldDefinition("code", SchemaType.str, optional=False, constraints={"length": 5})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"code": "ABC"})

        assert result.valid is False
        assert "Length 3 does not equal required 5" in result.errors[0].message

    def test_validate_constraints_email_format_valid(self):
        """Test email format constraint - valid case."""
        field_def = FieldDefinition("email", SchemaType.str, optional=False, constraints={"format": "email"})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"email": "user@example.com"})

        assert result.valid is True

    def test_validate_constraints_email_format_invalid(self):
        """Test email format constraint - invalid case."""
        field_def = FieldDefinition("email", SchemaType.str, optional=False, constraints={"format": "email"})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"email": "invalid-email"})

        assert result.valid is False
        assert "Invalid email format" in result.errors[0].message

    def test_validate_constraints_url_format_valid(self):
        """Test URL format constraint - valid case."""
        field_def = FieldDefinition("website", SchemaType.str, optional=False, constraints={"format": "url"})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"website": "https://example.com"})

        assert result.valid is True

    def test_validate_constraints_url_format_invalid(self):
        """Test URL format constraint - invalid case."""
        field_def = FieldDefinition("website", SchemaType.str, optional=False, constraints={"format": "url"})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"website": "not-a-url"})

        assert result.valid is False
        assert "Invalid URL format" in result.errors[0].message

    def test_validate_constraints_uuid_format_valid(self):
        """Test UUID format constraint - valid case."""
        field_def = FieldDefinition("id", SchemaType.str, optional=False, constraints={"format": "uuid"})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"id": "123e4567-e89b-12d3-a456-426614174000"})

        assert result.valid is True

    def test_validate_constraints_uuid_format_invalid(self):
        """Test UUID format constraint - invalid case."""
        field_def = FieldDefinition("id", SchemaType.str, optional=False, constraints={"format": "uuid"})
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"id": "not-a-uuid"})

        assert result.valid is False
        assert "Invalid UUID format" in result.errors[0].message

    def test_validate_constraints_no_comparison_methods(self):
        """Test constraints with value that has comparison but fails."""
        field_def = FieldDefinition("data", SchemaType.any, optional=False, constraints={"min": 10, "max": 100})
        self.schema_ast.fields = [field_def]

        # Valid value within constraints
        result = self.validator.validate_data({"data": 50})
        assert result.valid is True

        # Invalid value below minimum
        result = self.validator.validate_data({"data": 5})
        assert result.valid is False

    def test_validate_constraints_no_len_method(self):
        """Test length constraint with value that doesn't have __len__."""
        field_def = FieldDefinition("value", SchemaType.any, optional=False, constraints={"length": 5})
        self.schema_ast.fields = [field_def]

        # Object without __len__ should not cause errors
        result = self.validator.validate_data({"value": 123})

        assert result.valid is True

    def test_validate_element_type_custom_type(self):
        """Test validating list elements with custom types."""
        # Register custom type
        self.type_registry.register_type("positive_int", "Int", validator=lambda x: x > 0)

        field_def = FieldDefinition("scores", SchemaType.list, optional=False, element_types=["positive_int"])
        self.schema_ast.fields = [field_def]

        result = self.validator.validate_data({"scores": [10, 20, 30]})
        assert result.valid is True

        result = self.validator.validate_data({"scores": [10, -5, 30]})
        assert result.valid is False

    def test_complex_validation_scenario(self):
        """Test complex validation with multiple fields and constraints."""
        fields = [
            FieldDefinition("name", SchemaType.str, optional=False, constraints={"length": 5}),
            FieldDefinition("age", SchemaType.int, optional=False, constraints={"min": 18, "max": 100}),
            FieldDefinition("email", SchemaType.str, optional=True, constraints={"format": "email"}),
            FieldDefinition("scores", SchemaType.list, optional=False, element_types=["Int"]),
        ]
        self.schema_ast.fields = fields

        # Valid data
        valid_data = {"name": "Alice", "age": 25, "email": "alice@example.com", "scores": [85, 90, 78]}
        result = self.validator.validate_data(valid_data)
        assert result.valid is True

        # Invalid data (multiple errors)
        invalid_data = {
            "name": "Al",  # too short
            "age": 15,  # too young
            "email": "invalid-email",  # bad format
            "scores": [85, "not-int", 78],  # wrong element type
        }
        result = self.validator.validate_data(invalid_data)
        assert result.valid is False
        assert len(result.errors) >= 3  # Should have multiple errors
