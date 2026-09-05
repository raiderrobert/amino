# amino/runtime/validator.py
import re
from typing import Any

from amino.errors import DecisionValidationError
from amino.schema.registry import SchemaRegistry

_BASE_TYPES: dict[str, type] = {
    "Int": int, "Float": float, "Str": str, "Bool": bool,
}


def _check_type(value: Any, type_name: str) -> bool:
    if type_name in _BASE_TYPES:
        t = _BASE_TYPES[type_name]
        if type_name == "Float":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if type_name == "Int":
            return isinstance(value, int) and not isinstance(value, bool)
        return isinstance(value, t)
    return True  # custom types: base type checking deferred to type registry


def _check_constraints(value: Any, constraints: dict[str, Any]) -> str | None:
    for key, constraint_val in constraints.items():
        if key == "min" and value < constraint_val:
            return f"value {value} below min {constraint_val}"
        if key == "max" and value > constraint_val:
            return f"value {value} above max {constraint_val}"
        if key == "exclusiveMin" and value <= constraint_val:
            return f"value {value} not above exclusiveMin {constraint_val}"
        if key == "exclusiveMax" and value >= constraint_val:
            return f"value {value} not below exclusiveMax {constraint_val}"
        if key == "minLength" and len(value) < constraint_val:
            return f"length {len(value)} below minLength {constraint_val}"
        if key == "maxLength" and len(value) > constraint_val:
            return f"length {len(value)} above maxLength {constraint_val}"
        if key == "exactLength" and len(value) != constraint_val:
            return f"length must be {constraint_val}"
        if key == "pattern":
            if not re.fullmatch(constraint_val, value):
                return f"value does not match pattern {constraint_val!r}"
        if key == "oneOf" and value not in constraint_val:
            return f"value {value!r} not in {constraint_val}"
        if key == "const" and value != constraint_val:
            return f"value must equal {constraint_val!r}"
        if key == "minItems" and len(value) < constraint_val:
            return f"list length {len(value)} below minItems {constraint_val}"
        if key == "maxItems" and len(value) > constraint_val:
            return f"list length {len(value)} above maxItems {constraint_val}"
        if key == "unique" and constraint_val and len(value) != len(set(value)):
            return "list elements must be unique"
    return None


class DecisionValidator:
    def __init__(self, schema: SchemaRegistry, decisions_mode: str = "loose"):
        if decisions_mode not in ("strict", "loose"):
            raise ValueError(f"decisions_mode must be 'strict' or 'loose', got {decisions_mode!r}")
        self._schema = schema
        self._mode = decisions_mode

    def validate(self, decision: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        cleaned: dict[str, Any] = {}
        warnings: list[str] = []

        for f in self._schema._ast.fields:
            value = decision.get(f.name)
            # Missing field
            if f.name not in decision:
                if f.optional:
                    continue
                msg = f"Required field '{f.name}' is missing (required)"
                if self._mode == "strict":
                    raise DecisionValidationError(msg, field=f.name)
                warnings.append(msg)
                continue
            # Key present but value is None
            if value is None:
                if f.optional:
                    continue
                # Required field has explicit None — treat as type error
                msg = f"Field '{f.name}' expected {f.type_name}, got NoneType"
                if self._mode == "strict":
                    raise DecisionValidationError(msg, field=f.name)
                warnings.append(msg)
                continue
            # Type check
            if not _check_type(value, f.type_name):
                msg = f"Field '{f.name}' expected {f.type_name}, got {type(value).__name__}"
                if self._mode == "strict":
                    raise DecisionValidationError(msg, field=f.name)
                warnings.append(msg)
                continue
            # Constraints
            if f.constraints:
                violation = _check_constraints(value, f.constraints)
                if violation:
                    msg = f"Field '{f.name}' constraint violation: {violation}"
                    if self._mode == "strict":
                        raise DecisionValidationError(msg, field=f.name)
                    warnings.append(msg)
                    continue
            cleaned[f.name] = value

        # Pass through extra fields not in schema
        schema_field_names = {f.name for f in self._schema._ast.fields}
        for k, v in decision.items():
            if k not in cleaned and k not in schema_field_names:
                cleaned[k] = v

        return cleaned, warnings
