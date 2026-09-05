# tests/test_decision_validator.py
import pytest
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.runtime.validator import DecisionValidator
from amino.errors import DecisionValidationError

def _validator(schema: str, mode: str = "strict") -> DecisionValidator:
    return DecisionValidator(SchemaRegistry(parse_schema(schema)), decisions_mode=mode)

def test_valid_decision_passes():
    v = _validator("age: Int\nname: Str")
    cleaned, warnings = v.validate({"age": 25, "name": "Alice"})
    assert cleaned["age"] == 25 and warnings == []

def test_missing_required_strict_raises():
    v = _validator("age: Int")
    with pytest.raises(DecisionValidationError, match="required"):
        v.validate({"name": "Alice"})

def test_missing_required_loose_warns():
    v = _validator("age: Int", mode="loose")
    cleaned, warnings = v.validate({"name": "Alice"})
    assert "age" not in cleaned
    assert any("age" in w for w in warnings)

def test_optional_field_missing_is_fine():
    v = _validator("email: Str?")
    cleaned, warnings = v.validate({})
    assert warnings == []

def test_optional_field_null_is_fine():
    v = _validator("email: Str?")
    cleaned, warnings = v.validate({"email": None})
    assert warnings == []

def test_constraint_violation_strict_raises():
    v = _validator("age: Int {min: 18}")
    with pytest.raises(DecisionValidationError, match="constraint"):
        v.validate({"age": 10})

def test_constraint_violation_loose_warns():
    v = _validator("age: Int {min: 18}", mode="loose")
    cleaned, warnings = v.validate({"age": 10})
    assert "age" not in cleaned
    assert any("age" in w for w in warnings)

def test_oneof_constraint():
    v = _validator("status: Str {oneOf: ['active', 'inactive']}")
    with pytest.raises(DecisionValidationError):
        v.validate({"status": "deleted"})

def test_no_type_coercion():
    v = _validator("age: Int", mode="loose")
    cleaned, warnings = v.validate({"age": "25"})
    assert "age" not in cleaned  # "25" is not Int, not coerced
    assert warnings
