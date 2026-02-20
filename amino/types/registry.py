"""Type registry implementation."""

import dataclasses
from collections.abc import Callable

from amino.errors import SchemaValidationError


@dataclasses.dataclass
class TypeDef:
    name: str
    base: str   # 'Str' | 'Int' | 'Float' | 'Bool'
    validator: Callable[[object], bool]


class TypeRegistry:
    def __init__(self):
        self._types: dict[str, TypeDef] = {}

    def register_type(self, name: str, base: str, validator: Callable[[object], bool]) -> None:
        if name in self._types:
            raise SchemaValidationError(f"Type '{name}' already registered")
        if base not in ("Str", "Int", "Float", "Bool"):
            raise SchemaValidationError(f"Base type must be Str/Int/Float/Bool, got '{base}'")
        self._types[name] = TypeDef(name=name, base=base, validator=validator)

    def has_type(self, name: str) -> bool:
        return name in self._types

    def get_base(self, name: str) -> str | None:
        td = self._types.get(name)
        return td.base if td else None

    def validate(self, name: str, value: object) -> bool:
        td = self._types.get(name)
        if td is None:
            return False
        try:
            return bool(td.validator(value))
        except Exception:
            return False

    def registered_names(self) -> set[str]:
        return set(self._types)
