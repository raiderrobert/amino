"""Utility functions for Amino."""

from typing import Any


def flatten_dict(data: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    """Flatten a nested dictionary."""
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def is_reserved_name(name: str) -> bool:
    """Check if a name is reserved."""
    reserved = {"and", "or", "not", "in", "typeof", "is_valid"}
    return name.lower() in reserved
