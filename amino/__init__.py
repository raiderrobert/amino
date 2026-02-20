# amino/__init__.py
import pathlib
from collections.abc import Callable

from .engine import Engine
from .errors import (
    AminoError,
    DecisionValidationError,
    EngineAlreadyFrozenError,
    OperatorConflictError,
    RuleEvaluationError,
    RuleParseError,
    SchemaParseError,
    SchemaValidationError,
    TypeMismatchError,
)


def load_schema(
    source: str,
    *,
    funcs: dict[str, Callable] | None = None,
    rules_mode: str = "strict",
    decisions_mode: str = "loose",
    operators: str | list[str] = "standard",
) -> Engine:
    """Load schema from file path or raw schema text and return an Engine."""
    try:
        text = pathlib.Path(source).read_text()
    except (OSError, ValueError):
        text = source
    return Engine(
        text,
        funcs=funcs,
        rules_mode=rules_mode,
        decisions_mode=decisions_mode,
        operators=operators,
    )


__all__ = [
    "AminoError",
    "DecisionValidationError",
    "Engine",
    "EngineAlreadyFrozenError",
    "OperatorConflictError",
    "RuleEvaluationError",
    "RuleParseError",
    "SchemaParseError",
    "SchemaValidationError",
    "TypeMismatchError",
    "load_schema",
]
