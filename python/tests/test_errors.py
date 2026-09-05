# tests/test_errors.py
from amino.errors import (
    AminoError, SchemaParseError, SchemaValidationError, RuleParseError,
    TypeMismatchError, DecisionValidationError, RuleEvaluationError,
    OperatorConflictError, EngineAlreadyFrozenError,
)

def test_all_are_amino_errors():
    for cls in [SchemaParseError, SchemaValidationError, RuleParseError,
                TypeMismatchError, DecisionValidationError, RuleEvaluationError,
                OperatorConflictError, EngineAlreadyFrozenError]:
        assert issubclass(cls, AminoError)

def test_structured_fields():
    err = SchemaParseError("bad syntax", field="age", expected="Int", got="Str")
    assert err.message == "bad syntax"
    assert err.field == "age"
    assert err.expected == "Int"
    assert err.got == "Str"

def test_optional_fields_default_none():
    err = RuleParseError("unexpected token")
    assert err.field is None and err.expected is None and err.got is None
