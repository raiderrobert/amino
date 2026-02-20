"""Amino - Schema-first classification rules engine."""

__version__ = "0.1.0"

from collections.abc import Callable

from .engine import Engine


def load_schema(
    schema_text: str,
    *,
    funcs: dict[str, Callable] | None = None,
    rules_mode: str = "strict",
    decisions_mode: str = "loose",
    operators: str | list[str] = "standard",
) -> Engine:
    """Create an Engine from a schema string."""
    return Engine(
        schema_text,
        funcs=funcs,
        rules_mode=rules_mode,
        decisions_mode=decisions_mode,
        operators=operators,
    )


__all__ = ["Engine", "load_schema"]
