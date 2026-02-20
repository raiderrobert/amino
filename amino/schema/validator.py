# amino/schema/validator.py
from amino.errors import SchemaValidationError

from .ast import SchemaAST, SchemaType


class SchemaValidator:
    def __init__(self, ast: SchemaAST, known_custom_types: set[str] | None = None):
        self._ast = ast
        self._custom = known_custom_types or set()

    def validate(self) -> None:
        struct_names = {s.name for s in self._ast.structs}
        known = {"Int", "Float", "Str", "Bool", "List"} | struct_names | self._custom
        all_names: set[str] = set()

        for item in [*self._ast.fields, *self._ast.structs, *self._ast.functions]:
            name = item.name
            if name in all_names:
                raise SchemaValidationError(f"Duplicate name: '{name}'")
            all_names.add(name)

        for f in self._ast.fields:
            if f.schema_type == SchemaType.CUSTOM and f.type_name not in known:
                raise SchemaValidationError(f"Unknown type '{f.type_name}' in field '{f.name}'")

        for s in self._ast.structs:
            seen: set[str] = set()
            for f in s.fields:
                if f.name in seen:
                    raise SchemaValidationError(f"Duplicate field '{f.name}' in struct '{s.name}'")
                seen.add(f.name)
                if f.schema_type == SchemaType.CUSTOM and f.type_name not in known:
                    raise SchemaValidationError(f"Unknown type '{f.type_name}' in struct '{s.name}'")

        self._check_circular(struct_names)

    def _check_circular(self, struct_names: set[str]) -> None:
        struct_map = {s.name: s for s in self._ast.structs}

        def dfs(name: str, visiting: set[str]) -> None:
            if name in visiting:
                raise SchemaValidationError(f"Circular struct reference involving '{name}'")
            if name not in struct_map:
                return
            visiting = visiting | {name}
            for f in struct_map[name].fields:
                if f.schema_type == SchemaType.CUSTOM and f.type_name in struct_names:
                    dfs(f.type_name, visiting)

        for name in struct_names:
            dfs(name, set())
