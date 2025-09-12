"""Built-in type definitions."""

import re
from typing import Any

from .registry import TypeRegistry


class BuiltinTypes:
    """Container for built-in type validators."""

    @staticmethod
    def validate_email(value: Any) -> bool:
        """Validate email format."""
        if not isinstance(value, str):
            return False
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, value))

    @staticmethod
    def validate_url(value: Any) -> bool:
        """Validate URL format."""
        if not isinstance(value, str):
            return False
        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, value))

    @staticmethod
    def validate_uuid(value: Any) -> bool:
        """Validate UUID format."""
        if not isinstance(value, str):
            return False
        pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(pattern, value.lower()))

    @staticmethod
    def validate_phone(value: Any) -> bool:
        """Validate phone number format."""
        if not isinstance(value, str):
            return False
        # Simple phone validation - digits, spaces, dashes, parentheses
        pattern = r"^[\d\s\-\(\)\+]+$"
        return bool(re.match(pattern, value)) and len(re.sub(r"[^\d]", "", value)) >= 10

    @staticmethod
    def validate_ssn(value: Any) -> bool:
        """Validate SSN format (###-##-####)."""
        if not isinstance(value, str):
            return False
        pattern = r"^\d{3}-\d{2}-\d{4}$"
        return bool(re.match(pattern, value))

    @staticmethod
    def validate_credit_score(value: Any) -> bool:
        """Validate credit score range (300-850)."""
        if not isinstance(value, int):
            return False
        return 300 <= value <= 850

    @staticmethod
    def validate_currency(value: Any) -> bool:
        """Validate currency (non-negative number with up to 2 decimal places)."""
        if isinstance(value, int):
            return value >= 0
        if isinstance(value, float):
            return value >= 0.0 and round(value, 2) == value
        return False


def register_builtin_types(registry: TypeRegistry) -> None:
    """Register common built-in types with the registry."""

    # Email type
    registry.register_type(
        "email",
        "Str",
        validator=BuiltinTypes.validate_email,
        format_string="user@domain.com",
        description="Valid email address",
    )

    # URL type
    registry.register_type(
        "url", "Str", validator=BuiltinTypes.validate_url, format_string="https://example.com", description="Valid URL"
    )

    # UUID type
    registry.register_type(
        "uuid",
        "Str",
        validator=BuiltinTypes.validate_uuid,
        format_string="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        description="Valid UUID",
    )

    # Phone number type
    registry.register_type(
        "phone",
        "Str",
        validator=BuiltinTypes.validate_phone,
        format_string="(555) 123-4567",
        description="Valid phone number",
    )

    # SSN type
    registry.register_type(
        "ssn",
        "Str",
        validator=BuiltinTypes.validate_ssn,
        format_string="###-##-####",
        description="Valid Social Security Number",
    )

    # Credit score type
    registry.register_type(
        "credit_score",
        "Int",
        validator=BuiltinTypes.validate_credit_score,
        min=300,
        max=850,
        description="Valid credit score (300-850)",
    )

    # Currency type
    registry.register_type(
        "currency",
        "Float",
        validator=BuiltinTypes.validate_currency,
        min=0,
        precision=2,
        description="Non-negative currency amount",
    )

    # Positive integer
    registry.register_type(
        "positive_int", "Int", validator=lambda x: isinstance(x, int) and x > 0, min=1, description="Positive integer"
    )

    # Non-negative integer
    registry.register_type(
        "non_negative_int",
        "Int",
        validator=lambda x: isinstance(x, int) and x >= 0,
        min=0,
        description="Non-negative integer",
    )
