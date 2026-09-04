"""A parsed, type-checked expression ready to be compiled by a backend."""

import dataclasses

from amino.rules.ast import RuleAST
from amino.schema.registry import SchemaRegistry
from amino.types.registry import TypeRegistry


@dataclasses.dataclass(frozen=True)
class Expression:
    """Backend-agnostic typed AST plus the registries needed to interpret it.

    Produced by ``Engine.parse()``. Backends walk ``ast`` and use
    ``base_type`` to reduce custom types (``email``, ``ipv4``) to the
    primitive they are stored as.
    """

    ast: RuleAST
    schema: SchemaRegistry
    types: TypeRegistry

    def base_type(self, type_name: str) -> str:
        """Return the primitive base for ``type_name``.

        Primitives and ``List`` return themselves. Custom types return their
        registered base. Unknown names are returned unchanged.
        """
        base = self.types.get_base(type_name)
        return base if base is not None else type_name
