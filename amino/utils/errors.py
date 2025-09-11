"""Error definitions for Amino."""


class AminoError(Exception):
    """Base exception for all Amino errors."""

    pass


class SchemaParseError(AminoError):
    """Raised when schema parsing fails."""

    pass


class RuleParseError(AminoError):
    """Raised when rule parsing fails."""

    pass


class TypeValidationError(AminoError):
    """Raised when type validation fails."""

    pass


class RuleEvaluationError(AminoError):
    """Raised during rule evaluation."""

    pass
