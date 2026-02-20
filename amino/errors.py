class AminoError(Exception):
    def __init__(self, message: str, *, field: str | None = None,
                 expected: str | None = None, got: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field
        self.expected = expected
        self.got = got


class SchemaParseError(AminoError): pass
class SchemaValidationError(AminoError): pass
class RuleParseError(AminoError): pass
class TypeMismatchError(AminoError): pass
class DecisionValidationError(AminoError): pass
class RuleEvaluationError(AminoError): pass
class OperatorConflictError(AminoError): pass
class EngineAlreadyFrozenError(AminoError): pass
