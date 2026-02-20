from .ast import FieldDefinition, SchemaAST
from .validator import SchemaValidator


class SchemaRegistry:
    def __init__(self, ast: SchemaAST, known_custom_types: set[str] | None = None):
        self._ast = ast
        self._custom = known_custom_types or set()
        SchemaValidator(ast, self._custom).validate()
        self._struct_map = {s.name: s for s in ast.structs}
        self._fields: dict[str, FieldDefinition] = {}
        self._index()

    def _index(self) -> None:
        for f in self._ast.fields:
            self._fields[f.name] = f
            if f.type_name in self._struct_map:
                self._index_struct(f.name, f.type_name)

    def _index_struct(self, prefix: str, struct_name: str) -> None:
        s = self._struct_map.get(struct_name)
        if not s:
            return
        for f in s.fields:
            key = f"{prefix}.{f.name}"
            self._fields[key] = f
            if f.type_name in self._struct_map:
                self._index_struct(key, f.type_name)

    def get_field(self, path: str) -> FieldDefinition | None:
        return self._fields.get(path)

    def known_type_names(self) -> set[str]:
        return {"Int", "Float", "Str", "Bool"} | {s.name for s in self._ast.structs} | self._custom

    def export_schema(self) -> str:
        lines: list[str] = []
        for s in self._ast.structs:
            def _field_str(f):
                q = "?" if f.optional else ""
                c = ""
                if f.constraints:
                    pairs = ", ".join(f"{k}: {v!r}" for k, v in f.constraints.items())
                    c = f" {{{pairs}}}"
                return f"{f.name}: {f.type_name}{q}{c}"

            flds = ", ".join(_field_str(f) for f in s.fields)
            lines.append(f"struct {s.name} {{{flds}}}")
        for f in self._ast.fields:
            q = "?" if f.optional else ""
            c = ""
            if f.constraints:
                pairs = ", ".join(f"{k}: {v!r}" for k, v in f.constraints.items())
                c = f" {{{pairs}}}"
            lines.append(f"{f.name}: {f.type_name}{q}{c}")
        for fn in self._ast.functions:
            params = ", ".join(f"{p.name}: {p.type_name}" for p in fn.parameters)
            lines.append(f"{fn.name}: ({params}) -> {fn.return_type_name}")
        return "\n".join(lines)
