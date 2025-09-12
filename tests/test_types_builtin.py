"""Tests for amino.types.builtin module."""

from amino.types.builtin import BuiltinTypes, register_builtin_types
from amino.types.registry import TypeRegistry


class TestBuiltinTypes:
    """Tests for BuiltinTypes class."""

    def test_validate_email_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.uk",
            "user+label@domain.org",
            "user123@test-domain.com",
            "a@b.co",
            "very.long.email.address@very.long.domain.name.com",
        ]

        for email in valid_emails:
            assert BuiltinTypes.validate_email(email) is True, f"Failed for: {email}"

    def test_validate_email_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "user.domain.com",
            "",
            "user@domain.c",  # TLD too short
            "user name@domain.com",  # space in local part
            "user@domain .com",  # space in domain
        ]

        for email in invalid_emails:
            assert BuiltinTypes.validate_email(email) is False, f"Should fail for: {email}"

    def test_validate_email_non_string(self):
        """Test email validation with non-string inputs."""
        non_strings = [123, None, [], {}, True, 12.34]

        for value in non_strings:
            assert BuiltinTypes.validate_email(value) is False

    def test_validate_url_valid(self):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "https://www.example.com",
            "http://subdomain.example.com/path",
            "https://example.com/path?query=value",
            "https://example.com:8080",
            "http://192.168.1.1",
        ]

        for url in valid_urls:
            assert BuiltinTypes.validate_url(url) is True, f"Failed for: {url}"

    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "ftp://example.com",  # not http/https
            "example.com",  # missing protocol
            "http://",  # missing domain
            "",
            "not-a-url",
            "https:///invalid",
        ]

        for url in invalid_urls:
            assert BuiltinTypes.validate_url(url) is False, f"Should fail for: {url}"

    def test_validate_url_non_string(self):
        """Test URL validation with non-string inputs."""
        non_strings = [123, None, [], {}, True, 12.34]

        for value in non_strings:
            assert BuiltinTypes.validate_url(value) is False

    def test_validate_uuid_valid(self):
        """Test UUID validation with valid UUIDs."""
        valid_uuids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "550e8400-e29b-41d4-a716-446655440000",
            "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",  # uppercase
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",  # lowercase
            "12345678-1234-5678-9012-123456789012",
        ]

        for uuid in valid_uuids:
            assert BuiltinTypes.validate_uuid(uuid) is True, f"Failed for: {uuid}"

    def test_validate_uuid_invalid(self):
        """Test UUID validation with invalid UUIDs."""
        invalid_uuids = [
            "123e4567-e89b-12d3-a456-42661417400",  # too short
            "123e4567-e89b-12d3-a456-4266141740000",  # too long
            "123e4567-e89b-12d3-a456-42661417400g",  # invalid character
            "123e4567e89b12d3a456426614174000",  # missing dashes
            "123e4567-e89b-12d3-a456",  # incomplete
            "",
            "not-a-uuid",
        ]

        for uuid in invalid_uuids:
            assert BuiltinTypes.validate_uuid(uuid) is False, f"Should fail for: {uuid}"

    def test_validate_uuid_non_string(self):
        """Test UUID validation with non-string inputs."""
        non_strings = [123, None, [], {}, True, 12.34]

        for value in non_strings:
            assert BuiltinTypes.validate_uuid(value) is False

    def test_validate_phone_valid(self):
        """Test phone validation with valid phone numbers."""
        valid_phones = [
            "1234567890",  # 10 digits
            "123-456-7890",  # with dashes
            "(123) 456-7890",  # with parentheses
            "+1 123 456 7890",  # with country code
            "123 456 7890",  # with spaces
            "12345678901",  # 11 digits
            "+44 20 7946 0958",  # international
        ]

        for phone in valid_phones:
            assert BuiltinTypes.validate_phone(phone) is True, f"Failed for: {phone}"

    def test_validate_phone_invalid(self):
        """Test phone validation with invalid phone numbers."""
        invalid_phones = [
            "123456789",  # too few digits
            "abc-def-ghij",  # letters
            "123-456-789a",  # mixed letters and numbers
            "",
            "12345",  # too short
            "123@456#7890",  # invalid characters
        ]

        for phone in invalid_phones:
            assert BuiltinTypes.validate_phone(phone) is False, f"Should fail for: {phone}"

    def test_validate_phone_non_string(self):
        """Test phone validation with non-string inputs."""
        non_strings = [123, None, [], {}, True, 12.34]

        for value in non_strings:
            assert BuiltinTypes.validate_phone(value) is False

    def test_validate_ssn_valid(self):
        """Test SSN validation with valid SSNs."""
        valid_ssns = [
            "123-45-6789",
            "000-00-0000",
            "999-99-9999",
        ]

        for ssn in valid_ssns:
            assert BuiltinTypes.validate_ssn(ssn) is True, f"Failed for: {ssn}"

    def test_validate_ssn_invalid(self):
        """Test SSN validation with invalid SSNs."""
        invalid_ssns = [
            "123456789",  # no dashes
            "123-45-678",  # too short
            "123-45-67890",  # too long
            "12-345-6789",  # wrong format
            "123-456-789",  # wrong format
            "abc-de-fghi",  # letters
            "",
            "123-45-678a",  # mixed
        ]

        for ssn in invalid_ssns:
            assert BuiltinTypes.validate_ssn(ssn) is False, f"Should fail for: {ssn}"

    def test_validate_ssn_non_string(self):
        """Test SSN validation with non-string inputs."""
        non_strings = [123, None, [], {}, True, 12.34]

        for value in non_strings:
            assert BuiltinTypes.validate_ssn(value) is False

    def test_validate_credit_score_valid(self):
        """Test credit score validation with valid scores."""
        valid_scores = [300, 400, 600, 750, 850]

        for score in valid_scores:
            assert BuiltinTypes.validate_credit_score(score) is True, f"Failed for: {score}"

    def test_validate_credit_score_invalid(self):
        """Test credit score validation with invalid scores."""
        invalid_scores = [299, 851, 0, 1000, -100]

        for score in invalid_scores:
            assert BuiltinTypes.validate_credit_score(score) is False, f"Should fail for: {score}"

    def test_validate_credit_score_non_int(self):
        """Test credit score validation with non-integer inputs."""
        non_ints = ["500", 500.0, None, [], {}, True]

        for value in non_ints:
            assert BuiltinTypes.validate_credit_score(value) is False

    def test_validate_currency_valid_int(self):
        """Test currency validation with valid integer values."""
        valid_currencies = [0, 1, 100, 1000]

        for currency in valid_currencies:
            assert BuiltinTypes.validate_currency(currency) is True, f"Failed for: {currency}"

    def test_validate_currency_valid_float(self):
        """Test currency validation with valid float values."""
        valid_currencies = [0.0, 1.0, 10.50, 100.99, 0.01]

        for currency in valid_currencies:
            assert BuiltinTypes.validate_currency(currency) is True, f"Failed for: {currency}"

    def test_validate_currency_invalid_negative(self):
        """Test currency validation with negative values."""
        invalid_currencies = [-1, -0.01, -100, -1000.50]

        for currency in invalid_currencies:
            assert BuiltinTypes.validate_currency(currency) is False, f"Should fail for: {currency}"

    def test_validate_currency_invalid_precision(self):
        """Test currency validation with too many decimal places."""
        invalid_currencies = [10.123, 0.001, 99.999]

        for currency in invalid_currencies:
            assert BuiltinTypes.validate_currency(currency) is False, f"Should fail for: {currency}"

    def test_validate_currency_invalid_type(self):
        """Test currency validation with invalid types."""
        invalid_types = ["10.50", None, [], {}]  # Remove True since it's a valid bool/int

        for value in invalid_types:
            assert BuiltinTypes.validate_currency(value) is False


class TestRegisterBuiltinTypes:
    """Tests for register_builtin_types function."""

    def test_register_all_builtin_types(self):
        """Test that all builtin types are registered."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        expected_types = [
            "email",
            "url",
            "uuid",
            "phone",
            "ssn",
            "credit_score",
            "currency",
            "positive_int",
            "non_negative_int",
        ]

        for type_name in expected_types:
            assert registry.has_type(type_name), f"Type {type_name} not registered"

    def test_email_type_registration(self):
        """Test email type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("email")
        assert type_def is not None
        assert type_def.base_type == "Str"
        assert type_def.format_string == "user@domain.com"
        assert type_def.description == "Valid email address"
        assert callable(type_def.validator)

    def test_url_type_registration(self):
        """Test URL type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("url")
        assert type_def is not None
        assert type_def.base_type == "Str"
        assert type_def.format_string == "https://example.com"
        assert type_def.description == "Valid URL"
        assert callable(type_def.validator)

    def test_uuid_type_registration(self):
        """Test UUID type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("uuid")
        assert type_def is not None
        assert type_def.base_type == "Str"
        assert type_def.format_string == "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        assert type_def.description == "Valid UUID"
        assert callable(type_def.validator)

    def test_phone_type_registration(self):
        """Test phone type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("phone")
        assert type_def is not None
        assert type_def.base_type == "Str"
        assert type_def.format_string == "(555) 123-4567"
        assert type_def.description == "Valid phone number"
        assert callable(type_def.validator)

    def test_ssn_type_registration(self):
        """Test SSN type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("ssn")
        assert type_def is not None
        assert type_def.base_type == "Str"
        assert type_def.format_string == "###-##-####"
        assert type_def.description == "Valid Social Security Number"
        assert callable(type_def.validator)

    def test_credit_score_type_registration(self):
        """Test credit score type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("credit_score")
        assert type_def is not None
        assert type_def.base_type == "Int"
        assert type_def.constraints["min"] == 300
        assert type_def.constraints["max"] == 850
        assert type_def.description == "Valid credit score (300-850)"
        assert callable(type_def.validator)

    def test_currency_type_registration(self):
        """Test currency type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("currency")
        assert type_def is not None
        assert type_def.base_type == "Float"
        assert type_def.constraints["min"] == 0
        assert type_def.constraints["precision"] == 2
        assert type_def.description == "Non-negative currency amount"
        assert callable(type_def.validator)

    def test_positive_int_type_registration(self):
        """Test positive_int type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("positive_int")
        assert type_def is not None
        assert type_def.base_type == "Int"
        assert type_def.constraints["min"] == 1
        assert type_def.description == "Positive integer"
        assert callable(type_def.validator)

    def test_non_negative_int_type_registration(self):
        """Test non_negative_int type registration details."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        type_def = registry.get_type("non_negative_int")
        assert type_def is not None
        assert type_def.base_type == "Int"
        assert type_def.constraints["min"] == 0
        assert type_def.description == "Non-negative integer"
        assert callable(type_def.validator)

    def test_lambda_validators_work(self):
        """Test that lambda validators for positive_int and non_negative_int work correctly."""
        registry = TypeRegistry()
        register_builtin_types(registry)

        positive_int_type = registry.get_type("positive_int")
        non_negative_int_type = registry.get_type("non_negative_int")

        assert positive_int_type is not None
        assert non_negative_int_type is not None
        assert positive_int_type.validator is not None
        assert non_negative_int_type.validator is not None

        positive_int_validator = positive_int_type.validator
        non_negative_int_validator = non_negative_int_type.validator

        # Test positive_int validator
        assert positive_int_validator(1) is True
        assert positive_int_validator(100) is True
        assert positive_int_validator(0) is False
        assert positive_int_validator(-1) is False
        assert positive_int_validator("1") is False

        # Test non_negative_int validator
        assert non_negative_int_validator(0) is True
        assert non_negative_int_validator(1) is True
        assert non_negative_int_validator(100) is True
        assert non_negative_int_validator(-1) is False
        assert non_negative_int_validator("0") is False
