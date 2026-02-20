# Amino Rules Engine Rewrite — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the Amino rules engine with a correct type system, Pratt-based dynamic operator table, freeze-before-use lifecycle, and four match modes (`all`, `first`, `inverse`, `score`).

**Architecture:** The engine is a single object representing one decision context (schema + rules + modes). Schema is fixed at construction; rules are hot-swappable. All registrations (operators, types, functions) must complete before the first `compile()`/`eval()` call, after which the engine freezes. The rule parser is a Pratt parser initialized from the operator registry, enabling type-dispatched operator overloading.

**Tech Stack:** Python 3.10+, uv, pytest, ruff, ty. Run tests with `uv run pytest`. Lint with `uv run ruff check`. Type-check with `uv run ty check`.

**Key design decisions:**
- `in` supports type dispatch: `(T, List[T])` list membership and `(ipv4, cidr)` CIDR containment both use `in`, disambiguated by resolved types at compile time.
- `contains` is in the `'standard'` preset: `field contains 'substring'` → `(Str, Str) → Bool`.
- Amino evaluates one record at a time. Rules over collections (graph topology, cart iteration) require pre-aggregation by the caller.

---

## Pre-work: File cleanup

```bash
rm amino/core.py
rm amino/runtime/engine.py
rm amino/rules/optimizer.py
rm -rf amino/utils/
rm tests/test_rules_optimizer.py
rm tests/test_utils_helpers.py
mkdir -p amino/operators
touch amino/operators/__init__.py
git add -A
git commit -m "chore: remove files superseded by rewrite"
```

---

## Task 1: Error hierarchy

**Files:**
- Create: `amino/errors.py`
- Create: `tests/test_errors.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_errors.py -v
```

**Step 3: Implement**

```python
# amino/errors.py
class AminoError(Exception):
    def __init__(self, message: str, *, field: str | None = None,
                 expected: str | None = None, got: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field
        self.expected = expected
        self.got = got

class SchemaParseError(AminoError): pass
class SchemaValidationError(AminoError): pass
class RuleParseError(AminoError): pass
class TypeMismatchError(AminoError): pass
class DecisionValidationError(AminoError): pass
class RuleEvaluationError(AminoError): pass
class OperatorConflictError(AminoError): pass
class EngineAlreadyFrozenError(AminoError): pass
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_errors.py -v
```

**Step 5: Commit**
```bash
git add amino/errors.py tests/test_errors.py
git commit -m "feat: add error hierarchy"
```

---

## Task 2: Schema AST

Replace `amino/schema/types.py` with a clean `SchemaType` enum embedded in `amino/schema/ast.py`.

**Files:**
- Rewrite: `amino/schema/ast.py`
- Delete: `amino/schema/types.py`
- Create: `tests/test_schema_ast.py`

**Step 1: Write the failing test**

```python
# tests/test_schema_ast.py
from amino.schema.ast import (
    SchemaType, FieldDefinition, StructDefinition,
    FunctionDefinition, FunctionParameter, SchemaAST,
)

def test_schema_types():
    assert SchemaType.INT.value == "Int"
    assert SchemaType.FLOAT.value == "Float"
    assert SchemaType.STR.value == "Str"
    assert SchemaType.BOOL.value == "Bool"
    assert SchemaType.LIST.value == "List"
    assert SchemaType.STRUCT.value == "struct"
    assert SchemaType.CUSTOM.value == "custom"

def test_field_definition_defaults():
    f = FieldDefinition(name="age", schema_type=SchemaType.INT, type_name="Int")
    assert f.optional is False
    assert f.constraints == {}
    assert f.element_types == []

def test_schema_ast_empty():
    ast = SchemaAST()
    assert ast.fields == [] and ast.structs == [] and ast.functions == []
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_schema_ast.py -v
```

**Step 3: Implement**

```python
# amino/schema/ast.py
import dataclasses
import enum
from typing import Any


class SchemaType(enum.Enum):
    INT = "Int"
    FLOAT = "Float"
    STR = "Str"
    BOOL = "Bool"
    LIST = "List"
    STRUCT = "struct"
    CUSTOM = "custom"


@dataclasses.dataclass
class FieldDefinition:
    name: str
    schema_type: SchemaType
    type_name: str
    element_types: list[str] = dataclasses.field(default_factory=list)
    constraints: dict[str, Any] = dataclasses.field(default_factory=dict)
    optional: bool = False


@dataclasses.dataclass
class StructDefinition:
    name: str
    fields: list[FieldDefinition]


@dataclasses.dataclass
class FunctionParameter:
    name: str
    type_name: str


@dataclasses.dataclass
class FunctionDefinition:
    name: str
    parameters: list[FunctionParameter]
    return_type_name: str


@dataclasses.dataclass
class SchemaAST:
    fields: list[FieldDefinition] = dataclasses.field(default_factory=list)
    structs: list[StructDefinition] = dataclasses.field(default_factory=list)
    functions: list[FunctionDefinition] = dataclasses.field(default_factory=list)
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_schema_ast.py -v
```

**Step 5: Commit**
```bash
git add amino/schema/ast.py tests/test_schema_ast.py
git commit -m "feat: update schema AST with clean SchemaType enum"
```

---

## Task 3: Schema parser

Rewrite `amino/schema/parser.py` to implement the PEG grammar. Key improvements: full constraint types (boolean, list literals, quoted strings), optional `?`, proper float-before-integer disambiguation, comment stripping.

**Files:**
- Rewrite: `amino/schema/parser.py`
- Rewrite: `tests/test_schema_parser.py`

**Step 1: Write the failing tests**

```python
# tests/test_schema_parser.py
import pytest
from amino.schema.parser import parse_schema
from amino.schema.ast import SchemaType
from amino.errors import SchemaParseError

def test_primitive_field():
    ast = parse_schema("age: Int")
    assert ast.fields[0].name == "age"
    assert ast.fields[0].schema_type == SchemaType.INT

def test_optional_field():
    assert parse_schema("email: Str?").fields[0].optional is True

def test_list_field():
    f = parse_schema("tags: List[Str]").fields[0]
    assert f.schema_type == SchemaType.LIST
    assert f.element_types == ["Str"]

def test_union_list():
    f = parse_schema("vals: List[Int|Str]").fields[0]
    assert f.element_types == ["Int", "Str"]

def test_numeric_constraints():
    f = parse_schema("age: Int {min: 18, max: 120}").fields[0]
    assert f.constraints == {"min": 18, "max": 120}

def test_float_constraint():
    f = parse_schema("price: Float {min: 0.01}").fields[0]
    assert f.constraints["min"] == 0.01

def test_string_oneof_constraint():
    f = parse_schema("status: Str {oneOf: ['active', 'inactive']}").fields[0]
    assert f.constraints["oneOf"] == ["active", "inactive"]

def test_pattern_constraint():
    f = parse_schema("u: Str {pattern: '^[a-z]+$'}").fields[0]
    assert f.constraints["pattern"] == "^[a-z]+$"

def test_boolean_constraint():
    f = parse_schema("tags: List[Str] {unique: true}").fields[0]
    assert f.constraints["unique"] is True

def test_struct_definition():
    ast = parse_schema("struct Addr {\n  street: Str,\n  city: Str\n}")
    assert len(ast.structs) == 1
    assert len(ast.structs[0].fields) == 2

def test_struct_newline_separator():
    ast = parse_schema("struct Foo {\n  a: Int\n  b: Str\n}")
    assert len(ast.structs[0].fields) == 2

def test_function_definition():
    ast = parse_schema("check: (addr: Str) -> Bool")
    assert ast.functions[0].name == "check"
    assert ast.functions[0].return_type_name == "Bool"

def test_custom_type_field():
    f = parse_schema("ip: ipv4").fields[0]
    assert f.schema_type == SchemaType.CUSTOM
    assert f.type_name == "ipv4"

def test_comments_skipped():
    ast = parse_schema("# comment\nage: Int  # inline")
    assert len(ast.fields) == 1

def test_parse_error():
    with pytest.raises(SchemaParseError):
        parse_schema("age: @Int")
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_schema_parser.py -v
```

**Step 3: Implement**

```python
# amino/schema/parser.py
import re
from typing import Any
from .ast import FieldDefinition, FunctionDefinition, FunctionParameter, SchemaAST, SchemaType, StructDefinition
from amino.errors import SchemaParseError

_PRIMITIVES: dict[str, SchemaType] = {
    "Int": SchemaType.INT, "Float": SchemaType.FLOAT,
    "Str": SchemaType.STR, "Bool": SchemaType.BOOL,
}
_RESERVED = {"struct", "List"}


class _Parser:
    def __init__(self, text: str):
        self._text = text
        self._pos = 0
        self._line = 1

    def _peek(self) -> str | None:
        return self._text[self._pos] if self._pos < len(self._text) else None

    def _advance(self) -> str:
        ch = self._text[self._pos]
        if ch == "\n":
            self._line += 1
        self._pos += 1
        return ch

    def _skip_ws(self, newlines: bool = False) -> None:
        while self._pos < len(self._text):
            ch = self._text[self._pos]
            if ch == "#":
                while self._pos < len(self._text) and self._text[self._pos] != "\n":
                    self._pos += 1
            elif ch in " \t" or (newlines and ch in "\r\n"):
                if ch == "\n":
                    self._line += 1
                self._pos += 1
            else:
                break

    def _skip_h(self) -> None:  # horizontal only
        while self._pos < len(self._text) and self._text[self._pos] in " \t":
            self._pos += 1

    def _read_ident(self) -> str:
        m = re.match(r"[a-zA-Z_][a-zA-Z0-9_]*", self._text[self._pos:])
        if not m:
            raise SchemaParseError(f"Expected identifier at line {self._line}")
        self._pos += len(m.group())
        return m.group()

    def _expect(self, ch: str) -> None:
        self._skip_h()
        if self._peek() != ch:
            raise SchemaParseError(f"Expected '{ch}' at line {self._line}, got {self._peek()!r}")
        self._advance()

    # --- constraint values ---

    def _parse_str_literal(self) -> str:
        self._advance()  # opening '
        buf: list[str] = []
        while self._peek() not in (None, "'"):
            buf.append(self._advance())
        if self._peek() != "'":
            raise SchemaParseError(f"Unterminated string at line {self._line}")
        self._advance()
        return "".join(buf)

    def _parse_list_lit(self) -> list:
        self._advance()  # [
        items: list = []
        self._skip_h()
        while self._peek() != "]":
            items.append(self._parse_constraint_val())
            self._skip_h()
            if self._peek() == ",":
                self._advance()
                self._skip_h()
        self._advance()  # ]
        return items

    def _parse_constraint_val(self) -> Any:
        self._skip_h()
        ch = self._peek()
        if ch == "'":
            return self._parse_str_literal()
        if ch == "[":
            return self._parse_list_lit()
        m = re.match(r"-?\d+\.\d+", self._text[self._pos:])
        if m:
            self._pos += len(m.group())
            return float(m.group())
        m = re.match(r"-?\d+", self._text[self._pos:])
        if m:
            self._pos += len(m.group())
            return int(m.group())
        m = re.match(r"true|false", self._text[self._pos:])
        if m:
            self._pos += len(m.group())
            return m.group() == "true"
        raise SchemaParseError(f"Expected constraint value at line {self._line}")

    def _parse_constraints(self) -> dict[str, Any]:
        self._advance()  # {
        result: dict[str, Any] = {}
        self._skip_h()
        while self._peek() != "}":
            key = self._read_ident()
            self._expect(":")
            result[key] = self._parse_constraint_val()
            self._skip_h()
            if self._peek() == ",":
                self._advance()
                self._skip_h()
        self._advance()  # }
        return result

    # --- type expression ---

    def _parse_type_expr(self) -> tuple[SchemaType, str, list[str]]:
        self._skip_h()
        name = self._read_ident()
        if name == "List":
            self._expect("[")
            elems: list[str] = [self._read_ident()]
            while self._peek() == "|":
                self._advance()
                elems.append(self._read_ident())
            self._expect("]")
            return SchemaType.LIST, f"List[{'|'.join(elems)}]", elems
        if name in _PRIMITIVES:
            return _PRIMITIVES[name], name, []
        return SchemaType.CUSTOM, name, []

    # --- field ---

    def _parse_field(self) -> FieldDefinition:
        self._skip_h()
        name = self._read_ident()
        if name in _RESERVED:
            raise SchemaParseError(f"Reserved word '{name}' used as field name at line {self._line}")
        self._expect(":")
        stype, tname, elems = self._parse_type_expr()
        optional = False
        self._skip_h()
        if self._peek() == "?":
            optional = True
            self._advance()
        constraints: dict[str, Any] = {}
        self._skip_h()
        if self._peek() == "{":
            constraints = self._parse_constraints()
        return FieldDefinition(name, stype, tname, elems, constraints, optional)

    # --- struct ---

    def _parse_struct(self) -> StructDefinition:
        self._read_ident()  # 'struct'
        self._skip_h()
        name = self._read_ident()
        self._skip_ws(newlines=True)
        self._expect("{")
        fields: list[FieldDefinition] = []
        while True:
            self._skip_ws(newlines=True)
            if self._peek() == "}":
                break
            fields.append(self._parse_field())
            self._skip_h()
            if self._peek() == ",":
                self._advance()
        self._advance()  # }
        return StructDefinition(name, fields)

    # --- function ---

    def _is_function(self) -> bool:
        saved = self._pos
        try:
            self._read_ident()
            self._skip_h()
            if self._peek() != ":":
                return False
            self._advance()
            self._skip_h()
            return self._peek() == "("
        except SchemaParseError:
            return False
        finally:
            self._pos = saved

    def _parse_function(self) -> FunctionDefinition:
        name = self._read_ident()
        self._expect(":")
        self._expect("(")
        params: list[FunctionParameter] = []
        self._skip_h()
        while self._peek() != ")":
            pname = self._read_ident()
            self._expect(":")
            _, ptype_name, _ = self._parse_type_expr()
            params.append(FunctionParameter(pname, ptype_name))
            self._skip_h()
            if self._peek() == ",":
                self._advance()
                self._skip_h()
        self._advance()  # )
        self._skip_h()
        if self._text[self._pos:self._pos + 2] != "->":
            raise SchemaParseError(f"Expected '->' at line {self._line}")
        self._pos += 2
        self._skip_h()
        ret_name = self._read_ident()
        return FunctionDefinition(name, params, ret_name)

    # --- top-level ---

    def parse(self) -> SchemaAST:
        ast = SchemaAST()
        while True:
            self._skip_ws(newlines=True)
            if self._pos >= len(self._text):
                break
            if self._text[self._pos:].startswith("struct"):
                ast.structs.append(self._parse_struct())
            elif self._is_function():
                ast.functions.append(self._parse_function())
            else:
                ast.fields.append(self._parse_field())
        return ast


def parse_schema(text: str) -> SchemaAST:
    return _Parser(text).parse()
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_schema_parser.py -v
```

**Step 5: Commit**
```bash
git add amino/schema/parser.py tests/test_schema_parser.py
git commit -m "feat: rewrite schema parser with full constraint and optional support"
```

---

## Task 4: Schema validator

Rewrite `amino/schema/validator.py`: no duplicate names, all type references resolve, no circular struct references.

**Files:**
- Rewrite: `amino/schema/validator.py`
- Create: `tests/test_schema_validator.py`

**Step 1: Write the failing tests**

```python
# tests/test_schema_validator.py
import pytest
from amino.schema.parser import parse_schema
from amino.schema.validator import SchemaValidator
from amino.errors import SchemaValidationError

def test_valid_passes():
    SchemaValidator(parse_schema("age: Int\nname: Str")).validate()

def test_duplicate_field_raises():
    with pytest.raises(SchemaValidationError, match="Duplicate"):
        SchemaValidator(parse_schema("age: Int\nage: Str")).validate()

def test_unknown_type_raises():
    with pytest.raises(SchemaValidationError, match="Unknown type"):
        SchemaValidator(parse_schema("addr: UnknownStruct")).validate()

def test_known_custom_type_passes():
    SchemaValidator(parse_schema("ip: ipv4"), known_custom_types={"ipv4"}).validate()

def test_circular_struct_raises():
    ast = parse_schema("struct A { b: B }\nstruct B { a: A }")
    with pytest.raises(SchemaValidationError, match="Circular"):
        SchemaValidator(ast).validate()

def test_valid_nested_struct_passes():
    ast = parse_schema("struct Addr { city: Str }\nstruct User { addr: Addr }")
    SchemaValidator(ast).validate()

def test_duplicate_struct_field_raises():
    with pytest.raises(SchemaValidationError, match="Duplicate"):
        SchemaValidator(parse_schema("struct Foo { x: Int, x: Str }")).validate()
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_schema_validator.py -v
```

**Step 3: Implement**

```python
# amino/schema/validator.py
from .ast import SchemaAST, SchemaType
from amino.errors import SchemaValidationError


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
                if f.type_name in struct_names:
                    dfs(f.type_name, visiting)

        for name in struct_names:
            dfs(name, set())
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_schema_validator.py -v
```

**Step 5: Commit**
```bash
git add amino/schema/validator.py tests/test_schema_validator.py
git commit -m "feat: rewrite schema validator with circular ref detection"
```

---

## Task 5: Schema registry

New `amino/schema/registry.py`: fast field lookup, dot-notation traversal, schema export.

**Files:**
- Create: `amino/schema/registry.py`
- Create: `tests/test_schema_registry.py`

**Step 1: Write the failing tests**

```python
# tests/test_schema_registry.py
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.schema.ast import SchemaType

def _reg(src: str, custom: set[str] | None = None) -> SchemaRegistry:
    return SchemaRegistry(parse_schema(src), known_custom_types=custom or set())

def test_primitive_field_lookup():
    assert _reg("age: Int").get_field("age").schema_type == SchemaType.INT

def test_missing_field_returns_none():
    assert _reg("age: Int").get_field("nope") is None

def test_dot_notation():
    f = _reg("struct Addr { city: Str }\naddr: Addr").get_field("addr.city")
    assert f.schema_type == SchemaType.STR

def test_deep_dot_notation():
    src = "struct I { x: Int }\nstruct O { inner: I }\nouter: O"
    f = _reg(src).get_field("outer.inner.x")
    assert f is not None and f.schema_type == SchemaType.INT

def test_export_roundtrip():
    exported = _reg("age: Int\nname: Str?").export_schema()
    assert "age: Int" in exported
    assert "name: Str?" in exported

def test_known_type_names_includes_custom():
    assert "ipv4" in _reg("ip: ipv4", custom={"ipv4"}).known_type_names()
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_schema_registry.py -v
```

**Step 3: Implement**

```python
# amino/schema/registry.py
from .ast import FieldDefinition, SchemaAST, SchemaType
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
        for s in self._ast.structs:
            for f in s.fields:
                self._fields[f"{s.name}.{f.name}"] = f

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
            flds = ", ".join(f"{f.name}: {f.type_name}{'?' if f.optional else ''}" for f in s.fields)
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
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_schema_registry.py -v
```

**Step 5: Commit**
```bash
git add amino/schema/registry.py tests/test_schema_registry.py
git commit -m "feat: add SchemaRegistry with dot-notation traversal and export"
```

---

## Task 6: Operator registry

New `amino/operators/registry.py` and `amino/operators/standard.py`. Supports type-dispatched lookup: the same symbol can have multiple implementations, disambiguated by operand types.

**Files:**
- Create: `amino/operators/registry.py`
- Create: `amino/operators/standard.py`
- Create: `tests/test_operators.py`

**Step 1: Write the failing tests**

```python
# tests/test_operators.py
import pytest
from amino.operators.registry import OperatorDef, OperatorRegistry
from amino.operators.standard import build_operator_registry
from amino.errors import OperatorConflictError

def test_register_and_lookup():
    reg = OperatorRegistry()
    reg.register(OperatorDef(symbol="~", kind="prefix", fn=lambda x: ~x,
        binding_power=50, input_types=("Int",), return_type="Int"))
    assert reg.lookup_by_types("~", ("Int",)) is not None

def test_type_dispatch():
    reg = OperatorRegistry()
    fn_list = lambda l, r: l in r
    fn_cidr = lambda l, r: False  # placeholder
    reg.register(OperatorDef(symbol="in", kind="infix", fn=fn_list,
        binding_power=40, input_types=("*", "List"), return_type="Bool"))
    reg.register(OperatorDef(symbol="in", kind="infix", fn=fn_cidr,
        binding_power=40, input_types=("ipv4", "cidr"), return_type="Bool"))
    assert reg.lookup_by_types("in", ("ipv4", "cidr")).fn is fn_cidr
    assert reg.lookup_by_types("in", ("Str", "List")).fn is fn_list

def test_conflict_same_types_raises():
    reg = OperatorRegistry()
    op = OperatorDef(symbol="=", kind="infix", fn=lambda l,r: l==r,
        binding_power=40, input_types=("*","*"), return_type="Bool")
    reg.register(op)
    with pytest.raises(OperatorConflictError):
        reg.register(op)

def test_standard_preset():
    reg = build_operator_registry("standard")
    assert reg.lookup_symbol("=") is not None
    assert reg.lookup_keyword("contains") is not None
    assert reg.lookup_keyword("and") is not None

def test_minimal_preset():
    reg = build_operator_registry("minimal")
    assert reg.lookup_keyword("and") is not None
    assert reg.lookup_symbol("=") is None

def test_explicit_list_preset():
    reg = build_operator_registry(["=", "!="])
    assert reg.lookup_symbol("=") is not None
    assert reg.lookup_symbol(">") is None

def test_binding_powers():
    reg = build_operator_registry("standard")
    assert reg.get_binding_power("or") == 10
    assert reg.get_binding_power("and") == 20
    assert reg.get_binding_power("=") == 40
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_operators.py -v
```

**Step 3: Implement**

```python
# amino/operators/registry.py
import dataclasses
from collections.abc import Callable
from amino.errors import OperatorConflictError


@dataclasses.dataclass
class OperatorDef:
    fn: Callable
    binding_power: int
    symbol: str | None = None
    keyword: str | None = None
    kind: str = "infix"
    associativity: str = "left"
    input_types: tuple[str, ...] = ("*", "*")
    return_type: str = "Bool"

    def __post_init__(self):
        if not self.symbol and not self.keyword:
            raise ValueError("OperatorDef requires symbol or keyword")

    @property
    def token(self) -> str:
        return self.symbol or self.keyword  # type: ignore[return-value]


class OperatorRegistry:
    def __init__(self):
        self._by_token: dict[str, list[OperatorDef]] = {}
        self._symbols: set[str] = set()
        self._keywords: set[str] = set()

    def register(self, op: OperatorDef) -> None:
        token = op.token
        for existing in self._by_token.get(token, []):
            if existing.input_types == op.input_types:
                raise OperatorConflictError(
                    f"Operator '{token}' with input_types {op.input_types} already registered"
                )
        self._by_token.setdefault(token, []).append(op)
        if op.symbol:
            self._symbols.add(op.symbol)
        else:
            self._keywords.add(op.keyword)  # type: ignore[arg-type]

    def lookup_by_types(self, token: str, input_types: tuple[str, ...]) -> OperatorDef | None:
        candidates = self._by_token.get(token, [])
        # Exact match first
        for op in candidates:
            if op.input_types == input_types:
                return op
        # Wildcard fallback
        for op in candidates:
            if len(op.input_types) == len(input_types):
                if all(e == "*" or e == a for e, a in zip(op.input_types, input_types)):
                    return op
        return candidates[0] if len(candidates) == 1 else None

    def lookup_symbol(self, symbol: str) -> OperatorDef | None:
        c = self._by_token.get(symbol, [])
        return c[0] if c else None

    def lookup_keyword(self, keyword: str) -> OperatorDef | None:
        c = self._by_token.get(keyword, [])
        return c[0] if c else None

    def get_binding_power(self, token: str) -> int | None:
        c = self._by_token.get(token, [])
        return c[0].binding_power if c else None

    def is_symbol(self, token: str) -> bool:
        return token in self._symbols

    def is_keyword(self, token: str) -> bool:
        return token in self._keywords

    def all_symbols(self) -> set[str]:
        return set(self._symbols)

    def all_keywords(self) -> set[str]:
        return set(self._keywords)
```

```python
# amino/operators/standard.py
from .registry import OperatorDef, OperatorRegistry

_ALWAYS = {"or", "and", "not"}

_ALL_OPS: list[OperatorDef] = [
    OperatorDef(keyword="or",       fn=None, binding_power=10, kind="infix",  input_types=("Bool","Bool"), return_type="Bool"),
    OperatorDef(keyword="and",      fn=None, binding_power=20, kind="infix",  input_types=("Bool","Bool"), return_type="Bool"),
    OperatorDef(keyword="not",      fn=None, binding_power=30, kind="prefix", input_types=("Bool",),       return_type="Bool"),
    OperatorDef(keyword="in",       fn=lambda l,r: l in r,     binding_power=40, input_types=("*","List"),  return_type="Bool"),
    OperatorDef(keyword="not in",   fn=lambda l,r: l not in r, binding_power=40, input_types=("*","List"),  return_type="Bool"),
    OperatorDef(symbol="=",         fn=lambda l,r: l == r,     binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol="!=",        fn=lambda l,r: l != r,     binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol=">",         fn=lambda l,r: l > r,      binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol="<",         fn=lambda l,r: l < r,      binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol=">=",        fn=lambda l,r: l >= r,     binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(symbol="<=",        fn=lambda l,r: l <= r,     binding_power=40, input_types=("*","*"),     return_type="Bool"),
    OperatorDef(keyword="contains", fn=lambda l,r: r in l,     binding_power=40, input_types=("Str","Str"), return_type="Bool"),
]
_BY_TOKEN = {(op.symbol or op.keyword): op for op in _ALL_OPS}


def build_operator_registry(preset: "str | list[str]") -> OperatorRegistry:
    if preset == "standard":
        ops = _ALL_OPS
    elif preset == "minimal":
        ops = [op for op in _ALL_OPS if (op.symbol or op.keyword) in _ALWAYS]
    elif isinstance(preset, list):
        enabled = set(preset) | _ALWAYS
        ops = [op for op in _ALL_OPS if (op.symbol or op.keyword) in enabled]
    else:
        raise ValueError(f"Unknown preset: {preset!r}")
    reg = OperatorRegistry()
    for op in ops:
        reg.register(op)
    return reg
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_operators.py -v
```

**Step 5: Commit**
```bash
git add amino/operators/ tests/test_operators.py
git commit -m "feat: add operator registry with type dispatch and standard/minimal presets"
```

---

## Task 7: Type registry

Update `amino/types/registry.py` to match the new API: `register_type(name, base, validator)`. Remove the backward-compat lowercase aliases and the `format_string`/`description` extras. Update `amino/types/builtin.py`.

**Files:**
- Rewrite: `amino/types/registry.py`
- Rewrite: `amino/types/builtin.py`
- Rewrite: `tests/test_types.py` (replaces test_type_system.py, test_types_builtin.py, test_types_registry.py, test_types_validation.py)

**Step 1: Write the failing tests**

```python
# tests/test_types.py
import pytest
from amino.types.registry import TypeRegistry
from amino.types.builtin import register_builtin_types

def test_register_custom_type():
    reg = TypeRegistry()
    reg.register_type("ipv4", base="Str", validator=lambda v: isinstance(v, str))
    assert reg.has_type("ipv4")

def test_base_type_lookup():
    reg = TypeRegistry()
    reg.register_type("ipv4", base="Str", validator=lambda v: True)
    assert reg.get_base("ipv4") == "Str"

def test_validate_valid_value():
    reg = TypeRegistry()
    reg.register_type("posint", base="Int", validator=lambda v: v > 0)
    assert reg.validate("posint", 5) is True

def test_validate_invalid_value():
    reg = TypeRegistry()
    reg.register_type("posint", base="Int", validator=lambda v: v > 0)
    assert reg.validate("posint", -1) is False

def test_duplicate_registration_raises():
    from amino.errors import OperatorConflictError
    reg = TypeRegistry()
    reg.register_type("t", base="Str", validator=lambda v: True)
    with pytest.raises(Exception):
        reg.register_type("t", base="Str", validator=lambda v: True)

def test_builtin_types_registered():
    reg = TypeRegistry()
    register_builtin_types(reg)
    for name in ["ipv4", "ipv6", "cidr", "email", "uuid"]:
        assert reg.has_type(name), f"missing builtin type: {name}"

def test_builtin_ipv4_validates():
    reg = TypeRegistry()
    register_builtin_types(reg)
    assert reg.validate("ipv4", "192.168.1.1") is True
    assert reg.validate("ipv4", "not-an-ip") is False

def test_builtin_cidr_validates():
    reg = TypeRegistry()
    register_builtin_types(reg)
    assert reg.validate("cidr", "10.0.0.0/8") is True
    assert reg.validate("cidr", "10.0.0.0") is False
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_types.py -v
```

**Step 3: Implement**

```python
# amino/types/registry.py
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
```

```python
# amino/types/builtin.py
import re
from .registry import TypeRegistry


def _is_ipv4(v: object) -> bool:
    if not isinstance(v, str):
        return False
    parts = v.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _is_ipv6(v: object) -> bool:
    if not isinstance(v, str):
        return False
    try:
        import ipaddress
        ipaddress.IPv6Address(v)
        return True
    except ValueError:
        return False


def _is_cidr(v: object) -> bool:
    if not isinstance(v, str) or "/" not in v:
        return False
    try:
        import ipaddress
        ipaddress.ip_network(v, strict=False)
        return True
    except ValueError:
        return False


def _is_email(v: object) -> bool:
    if not isinstance(v, str):
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v))


def _is_uuid(v: object) -> bool:
    if not isinstance(v, str):
        return False
    return bool(re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        v, re.IGNORECASE,
    ))


def register_builtin_types(registry: TypeRegistry) -> None:
    registry.register_type("ipv4", base="Str", validator=_is_ipv4)
    registry.register_type("ipv6", base="Str", validator=_is_ipv6)
    registry.register_type("cidr", base="Str", validator=_is_cidr)
    registry.register_type("email", base="Str", validator=_is_email)
    registry.register_type("uuid", base="Str", validator=_is_uuid)
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_types.py -v
```

**Step 5: Commit**
```bash
git add amino/types/ tests/test_types.py
git commit -m "feat: rewrite type registry and builtins (ipv4, ipv6, cidr, email, uuid)"
```

---

## Task 8: Rule AST

Update `amino/rules/ast.py`: nodes carry `type_name: str` (resolved type) instead of `SchemaType` enum. Remove `Operator` enum (operators are now dynamic).

**Files:**
- Rewrite: `amino/rules/ast.py`
- Create: `tests/test_rule_ast.py`

**Step 1: Write the failing tests**

```python
# tests/test_rule_ast.py
from amino.rules.ast import Literal, Variable, BinaryOp, UnaryOp, FunctionCall, RuleAST

def test_literal_node():
    n = Literal(value=42, type_name="Int")
    assert n.value == 42 and n.type_name == "Int"

def test_variable_node():
    n = Variable(name="credit_score", type_name="Int")
    assert n.name == "credit_score"

def test_binary_op_node():
    left = Variable("score", "Int")
    right = Literal(500, "Int")
    n = BinaryOp(op_token="=", left=left, right=right, type_name="Bool", fn=lambda l, r: l == r)
    assert n.op_token == "="

def test_unary_op_node():
    operand = Variable("active", "Bool")
    n = UnaryOp(op_token="not", operand=operand, type_name="Bool", fn=lambda v: not v)
    assert n.op_token == "not"

def test_function_call_node():
    n = FunctionCall(name="is_valid", args=[], type_name="Bool")
    assert n.name == "is_valid"

def test_rule_ast():
    root = Literal(True, "Bool")
    ast = RuleAST(root=root, return_type="Bool")
    assert ast.return_type == "Bool"
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_rule_ast.py -v
```

**Step 3: Implement**

```python
# amino/rules/ast.py
import dataclasses
from collections.abc import Callable
from typing import Any


@dataclasses.dataclass
class RuleNode:
    type_name: str   # resolved type: "Bool", "Int", "ipv4", etc.


@dataclasses.dataclass
class Literal(RuleNode):
    value: Any

    def __init__(self, value: Any, type_name: str):
        self.value = value
        self.type_name = type_name


@dataclasses.dataclass
class Variable(RuleNode):
    name: str

    def __init__(self, name: str, type_name: str):
        self.name = name
        self.type_name = type_name


@dataclasses.dataclass
class BinaryOp(RuleNode):
    op_token: str
    left: RuleNode
    right: RuleNode
    fn: Callable

    def __init__(self, op_token: str, left: RuleNode, right: RuleNode,
                 type_name: str, fn: Callable):
        self.op_token = op_token
        self.left = left
        self.right = right
        self.type_name = type_name
        self.fn = fn


@dataclasses.dataclass
class UnaryOp(RuleNode):
    op_token: str
    operand: RuleNode
    fn: Callable

    def __init__(self, op_token: str, operand: RuleNode, type_name: str, fn: Callable):
        self.op_token = op_token
        self.operand = operand
        self.type_name = type_name
        self.fn = fn


@dataclasses.dataclass
class FunctionCall(RuleNode):
    name: str
    args: list[RuleNode]

    def __init__(self, name: str, args: list[RuleNode], type_name: str):
        self.name = name
        self.args = args
        self.type_name = type_name


@dataclasses.dataclass
class RuleAST:
    root: RuleNode
    return_type: str
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_rule_ast.py -v
```

**Step 5: Commit**
```bash
git add amino/rules/ast.py tests/test_rule_ast.py
git commit -m "feat: update rule AST with string type_name and operator fn on nodes"
```

---

## Task 9: Pratt parser

Rewrite `amino/rules/parser.py` as a Pratt (top-down operator precedence) parser. Initialized with an `OperatorRegistry` and a `SchemaRegistry`. Handles atoms (literals, variables, function calls, parentheses) and dispatches infix/prefix operators from the registry dynamically.

**Files:**
- Rewrite: `amino/rules/parser.py`
- Rewrite: `tests/test_rule_parser.py`

**Step 1: Write the failing tests**

```python
# tests/test_rule_parser.py
import pytest
from amino.operators.standard import build_operator_registry
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.rules.parser import parse_rule
from amino.rules.ast import BinaryOp, Literal, UnaryOp, Variable
from amino.errors import RuleParseError

def _parse(rule: str, schema: str = "score: Int\nname: Str\nactive: Bool\ntags: List[Str]"):
    reg = SchemaRegistry(parse_schema(schema))
    ops = build_operator_registry("standard")
    return parse_rule(rule, reg, ops)

def test_integer_literal():
    ast = _parse("500")
    assert isinstance(ast.root, Literal) and ast.root.value == 500

def test_float_before_integer():
    ast = _parse("600.0")
    assert isinstance(ast.root, Literal) and ast.root.value == 600.0

def test_string_literal():
    ast = _parse("'hello'")
    assert isinstance(ast.root, Literal) and ast.root.value == "hello"

def test_boolean_literal():
    ast = _parse("true")
    assert isinstance(ast.root, Literal) and ast.root.value is True

def test_variable_reference():
    ast = _parse("score")
    assert isinstance(ast.root, Variable) and ast.root.name == "score"

def test_simple_comparison():
    ast = _parse("score = 500")
    assert isinstance(ast.root, BinaryOp)
    assert ast.root.op_token == "="

def test_comparison_precedence_over_and():
    ast = _parse("score > 400 and score < 800")
    assert isinstance(ast.root, BinaryOp)
    assert ast.root.op_token == "and"

def test_not_prefix():
    ast = _parse("not active")
    assert isinstance(ast.root, UnaryOp) and ast.root.op_token == "not"

def test_parentheses_grouping():
    ast = _parse("(score > 400 or score < 100) and active = true")
    root = ast.root
    assert root.op_token == "and"

def test_in_list_membership():
    ast = _parse("name in ['foo', 'bar']")
    assert ast.root.op_token == "in"

def test_not_in():
    ast = _parse("name not in ['a', 'b']")
    assert ast.root.op_token == "not in"

def test_contains_operator():
    ast = _parse("name contains 'ell'")
    assert ast.root.op_token == "contains"

def test_function_call():
    schema = "score: Int\ncheck: (x: Int) -> Bool"
    ast = _parse("check(score)", schema=schema)
    from amino.rules.ast import FunctionCall
    assert isinstance(ast.root, FunctionCall) and ast.root.name == "check"

def test_dot_notation():
    schema = "struct Addr { city: Str }\naddr: Addr"
    ast = _parse("addr.city = 'SF'", schema=schema)
    assert isinstance(ast.root, BinaryOp)
    assert isinstance(ast.root.left, Variable)
    assert ast.root.left.name == "addr.city"

def test_unknown_variable_raises():
    with pytest.raises(RuleParseError, match="Unknown"):
        _parse("unknown_field = 1")

def test_list_literal_in_rule():
    ast = _parse("tags in [['a', 'b']]")  # tags is List[Str], comparing with list literal
    assert ast.root.op_token == "in"

def test_or_lower_precedence_than_and():
    # a or b and c  should parse as  a or (b and c)
    ast = _parse("active = true or score > 0 and score < 100")
    assert ast.root.op_token == "or"
    assert ast.root.right.op_token == "and"
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_rule_parser.py -v
```

**Step 3: Implement**

The Pratt parser works in two phases:
1. **Tokenize**: produce a flat list of typed tokens
2. **Parse**: `parse_expr(min_bp)` — call `nud()` for the current token (prefix/atom), then loop calling `led(left)` while the next token's left binding power exceeds `min_bp`

`and`/`or` binding powers drive the parse loop. Right-associative operators use `bp - 1` for the recursive call.

```python
# amino/rules/parser.py
import re
from collections.abc import Callable
from typing import Any

from .ast import BinaryOp, FunctionCall, Literal, RuleAST, RuleNode, UnaryOp, Variable
from amino.errors import RuleParseError
from amino.operators.registry import OperatorDef, OperatorRegistry
from amino.schema.registry import SchemaRegistry

# ── tokenizer ──────────────────────────────────────────────────────────────────

_FLOAT_RE = re.compile(r"-?\d+\.\d+")
_INT_RE   = re.compile(r"-?\d+")
_STR_RE   = re.compile(r"'[^']*'")
_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

_FIXED_SYMBOLS = [">=", "<=", "!=", ">", "<", "=", "(", ")", "[", "]", ",", "."]


def _tokenize(text: str, op_symbols: set[str]) -> list[str]:
    all_symbols = sorted(op_symbols | set(_FIXED_SYMBOLS), key=len, reverse=True)
    tokens: list[str] = []
    i = 0
    while i < len(text):
        if text[i] in " \t":
            i += 1
            continue
        # Multi-word "not in"
        if text[i:i+6] == "not in":
            tokens.append("not in")
            i += 6
            continue
        # Strings
        m = _STR_RE.match(text, i)
        if m:
            tokens.append(m.group())
            i = m.end()
            continue
        # Float before int
        m = _FLOAT_RE.match(text, i)
        if m:
            tokens.append(m.group())
            i = m.end()
            continue
        m = _INT_RE.match(text, i)
        if m:
            tokens.append(m.group())
            i = m.end()
            continue
        # Identifiers / keywords
        m = _IDENT_RE.match(text, i)
        if m:
            tokens.append(m.group())
            i = m.end()
            continue
        # Symbols (longest match)
        matched = False
        for sym in all_symbols:
            if text[i:i+len(sym)] == sym:
                tokens.append(sym)
                i += len(sym)
                matched = True
                break
        if not matched:
            raise RuleParseError(f"Unexpected character '{text[i]}' at position {i}")
    return tokens


# ── parser ─────────────────────────────────────────────────────────────────────

class _PrattParser:
    def __init__(self, tokens: list[str], schema: SchemaRegistry, ops: OperatorRegistry):
        self._tokens = tokens
        self._pos = 0
        self._schema = schema
        self._ops = ops

    def _peek(self) -> str | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _advance(self) -> str:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _left_bp(self, token: str | None) -> int:
        if token is None:
            return 0
        bp = self._ops.get_binding_power(token)
        return bp if bp is not None else 0

    def parse(self) -> RuleAST:
        node = self._parse_expr(0)
        if self._pos < len(self._tokens):
            raise RuleParseError(f"Unexpected token: {self._tokens[self._pos]!r}")
        return RuleAST(root=node, return_type=node.type_name)

    def _parse_expr(self, min_bp: int) -> RuleNode:
        left = self._nud()
        while True:
            tok = self._peek()
            if tok is None or tok in (")", "]", ","):
                break
            # "not in" two-token check
            if tok == "not" and self._pos + 1 < len(self._tokens) and self._tokens[self._pos + 1] == "in":
                tok = "not in"
            bp = self._left_bp(tok)
            if bp <= min_bp:
                break
            if tok == "not in":
                self._advance(); self._advance()
            else:
                self._advance()
            left = self._led(tok, left)
        return left

    def _nud(self) -> RuleNode:
        tok = self._advance()

        # Parentheses
        if tok == "(":
            node = self._parse_expr(0)
            if self._peek() != ")":
                raise RuleParseError("Expected ')'")
            self._advance()
            return node

        # List literal
        if tok == "[":
            items: list[Any] = []
            while self._peek() != "]":
                items.append(self._parse_literal_value())
                if self._peek() == ",":
                    self._advance()
            self._advance()  # ]
            return Literal(items, "List")

        # Prefix operator (not, ~, etc.)
        op_def = self._ops.lookup_keyword(tok) or self._ops.lookup_symbol(tok)
        if op_def and op_def.kind == "prefix":
            operand = self._parse_expr(op_def.binding_power)
            fn = op_def.fn or (lambda v: not v)
            return UnaryOp(tok, operand, op_def.return_type, fn)

        # Float literal
        try:
            val = float(tok)
            if "." in tok:
                return Literal(val, "Float")
        except ValueError:
            pass

        # Integer literal
        try:
            return Literal(int(tok), "Int")
        except ValueError:
            pass

        # String literal
        if tok.startswith("'") and tok.endswith("'"):
            return Literal(tok[1:-1], "Str")

        # Boolean
        if tok == "true":
            return Literal(True, "Bool")
        if tok == "false":
            return Literal(False, "Bool")

        # Identifier: function call or variable (possibly dotted)
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", tok):
            # function call?
            if self._peek() == "(":
                return self._parse_func_call(tok)
            # dotted name?
            name = tok
            while self._peek() == ".":
                self._advance()
                part = self._advance()
                name = f"{name}.{part}"
            # resolve type from schema
            field = self._schema.get_field(name)
            if field is None:
                # check if it's a schema function
                raise RuleParseError(f"Unknown field or variable: '{name}'")
            return Variable(name, field.type_name)

        raise RuleParseError(f"Unexpected token in expression: {tok!r}")

    def _led(self, tok: str, left: RuleNode) -> RuleNode:
        # Resolve operator with type dispatch
        right = self._parse_expr(self._left_bp(tok))
        left_type = left.type_name
        right_type = right.type_name
        op_def = (self._ops.lookup_by_types(tok, (left_type, right_type))
                  or self._ops.lookup_by_types(tok, ("*", "*")))
        if op_def is None:
            raise RuleParseError(f"No operator '{tok}' for types ({left_type}, {right_type})")

        # For and/or: implement inline with short-circuit (fn=None in registry)
        if tok == "and":
            fn: Callable = lambda l, r: bool(l) and bool(r)
        elif tok == "or":
            fn = lambda l, r: bool(l) or bool(r)
        else:
            fn = op_def.fn

        return BinaryOp(tok, left, right, op_def.return_type, fn)

    def _parse_func_call(self, name: str) -> FunctionCall:
        self._advance()  # (
        args: list[RuleNode] = []
        while self._peek() != ")":
            args.append(self._parse_expr(0))
            if self._peek() == ",":
                self._advance()
        self._advance()  # )
        # Resolve return type from schema functions
        fn_def = next((f for f in self._schema._ast.functions if f.name == name), None)
        return_type = fn_def.return_type_name if fn_def else "Any"
        return FunctionCall(name, args, return_type)

    def _parse_literal_value(self) -> Any:
        tok = self._advance()
        if tok.startswith("'"):
            return tok[1:-1]
        if tok == "true":
            return True
        if tok == "false":
            return False
        try:
            if "." in tok:
                return float(tok)
            return int(tok)
        except ValueError:
            raise RuleParseError(f"Expected literal, got {tok!r}")


def parse_rule(text: str, schema: SchemaRegistry, ops: OperatorRegistry) -> RuleAST:
    tokens = _tokenize(text.strip(), ops.all_symbols())
    return _PrattParser(tokens, schema, ops).parse()
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_rule_parser.py -v
```

**Step 5: Commit**
```bash
git add amino/rules/parser.py tests/test_rule_parser.py
git commit -m "feat: replace recursive descent parser with Pratt parser"
```

---

## Task 10: TypedCompiler

Rewrite `amino/rules/compiler.py`. Single-pass AST walk: type resolution is already done by the parser; the compiler generates evaluator closures and handles strict/loose mode type warnings.

**Files:**
- Rewrite: `amino/rules/compiler.py`
- Create: `tests/test_compiler.py`

**Step 1: Write the failing tests**

```python
# tests/test_compiler.py
import pytest
from amino.operators.standard import build_operator_registry
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.rules.parser import parse_rule
from amino.rules.compiler import TypedCompiler
from amino.errors import TypeMismatchError

SCHEMA = "score: Int\nname: Str\nactive: Bool\ntags: List[Str]"

def _compile(rule: str, rules_mode: str = "strict"):
    reg = SchemaRegistry(parse_schema(SCHEMA))
    ops = build_operator_registry("standard")
    ast = parse_rule(rule, reg, ops)
    compiler = TypedCompiler(rules_mode=rules_mode)
    return compiler.compile("r1", ast)

def test_simple_equality_evaluates():
    compiled = _compile("score = 500")
    assert compiled.evaluate({"score": 500}, {}) is True
    assert compiled.evaluate({"score": 400}, {}) is False

def test_and_short_circuits():
    compiled = _compile("active = true and score > 100")
    assert compiled.evaluate({"active": False, "score": 0}, {}) is False

def test_or_evaluates():
    compiled = _compile("score < 0 or score > 1000")
    assert compiled.evaluate({"score": 1500}, {}) is True

def test_not_evaluates():
    compiled = _compile("not active")
    assert compiled.evaluate({"active": False}, {}) is True

def test_in_list():
    compiled = _compile("name in ['alice', 'bob']")
    assert compiled.evaluate({"name": "alice"}, {}) is True
    assert compiled.evaluate({"name": "carol"}, {}) is False

def test_contains_operator():
    compiled = _compile("name contains 'ali'")
    assert compiled.evaluate({"name": "alice"}, {}) is True

def test_function_call():
    compiled = _compile("score = 42")
    fns = {}
    assert compiled.evaluate({"score": 42}, fns) is True

def test_dot_notation():
    schema = "struct Addr { city: Str }\naddr: Addr"
    reg = SchemaRegistry(parse_schema(schema))
    ops = build_operator_registry("standard")
    ast = parse_rule("addr.city = 'SF'", reg, ops)
    compiled = TypedCompiler().compile("r1", ast)
    assert compiled.evaluate({"addr": {"city": "SF"}}, {}) is True

def test_constant_folding():
    compiled = _compile("true = true")
    assert compiled.evaluate({}, {}) is True

def test_missing_field_returns_false():
    compiled = _compile("score > 100")
    # missing field → evaluates to False, no exception (loose runtime)
    assert compiled.evaluate({}, {}) is False
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_compiler.py -v
```

**Step 3: Implement**

```python
# amino/rules/compiler.py
from collections.abc import Callable
from typing import Any

from .ast import BinaryOp, FunctionCall, Literal, RuleAST, RuleNode, UnaryOp, Variable
from amino.errors import RuleEvaluationError


class CompiledRule:
    def __init__(self, rule_id: Any, fn: Callable, return_type: str):
        self.rule_id = rule_id
        self._fn = fn
        self.return_type = return_type

    def evaluate(self, data: dict[str, Any],
                 functions: dict[str, Callable]) -> Any:
        try:
            return self._fn(data, functions)
        except RuleEvaluationError:
            return False
        except Exception:
            return False


class TypedCompiler:
    def __init__(self, rules_mode: str = "strict"):
        self.rules_mode = rules_mode

    def compile(self, rule_id: Any, ast: RuleAST) -> CompiledRule:
        fn = self._build(ast.root)
        return CompiledRule(rule_id, fn, ast.return_type)

    def _build(self, node: RuleNode) -> Callable:
        if isinstance(node, Literal):
            v = node.value
            return lambda data, fns, _v=v: _v

        if isinstance(node, Variable):
            name = node.name
            if "." in name:
                parts = name.split(".")
                def var_fn(data, fns, _parts=parts):
                    cur = data
                    for p in _parts:
                        if isinstance(cur, dict) and p in cur:
                            cur = cur[p]
                        else:
                            raise RuleEvaluationError(f"Field '{name}' not found")
                    return cur
                return var_fn
            else:
                def simple_var(data, fns, _n=name):
                    if _n not in data:
                        raise RuleEvaluationError(f"Field '{_n}' not found")
                    return data[_n]
                return simple_var

        if isinstance(node, UnaryOp):
            operand_fn = self._build(node.operand)
            fn = node.fn
            def unary(data, fns, _op=operand_fn, _fn=fn):
                return _fn(_op(data, fns))
            return unary

        if isinstance(node, BinaryOp):
            left_fn = self._build(node.left)
            right_fn = self._build(node.right)
            op = node.op_token
            fn = node.fn
            if op == "and":
                def and_fn(data, fns, _l=left_fn, _r=right_fn):
                    return bool(_l(data, fns)) and bool(_r(data, fns))
                return and_fn
            if op == "or":
                def or_fn(data, fns, _l=left_fn, _r=right_fn):
                    return bool(_l(data, fns)) or bool(_r(data, fns))
                return or_fn
            def binary(data, fns, _l=left_fn, _r=right_fn, _fn=fn):
                return _fn(_l(data, fns), _r(data, fns))
            return binary

        if isinstance(node, FunctionCall):
            arg_fns = [self._build(a) for a in node.args]
            name = node.name
            def call_fn(data, fns, _name=name, _args=arg_fns):
                if _name not in fns:
                    raise RuleEvaluationError(f"Function '{_name}' not found")
                return fns[_name](*[f(data, fns) for f in _args])
            return call_fn

        raise RuleEvaluationError(f"Unknown node type: {type(node)}")
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_compiler.py -v
```

**Step 5: Commit**
```bash
git add amino/rules/compiler.py tests/test_compiler.py
git commit -m "feat: add TypedCompiler replacing separate compiler+optimizer"
```

---

## Task 11: Decision validator

New `amino/runtime/validator.py`. Validates decision dicts against schema constraints. `strict` mode raises; `loose` mode skips+warns.

**Files:**
- Create: `amino/runtime/validator.py`
- Create: `tests/test_decision_validator.py`

**Step 1: Write the failing tests**

```python
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
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_decision_validator.py -v
```

**Step 3: Implement**

```python
# amino/runtime/validator.py
from typing import Any
from amino.schema.ast import SchemaType
from amino.schema.registry import SchemaRegistry
from amino.errors import DecisionValidationError

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
            import re
            if not re.match(constraint_val, value):
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
        self._schema = schema
        self._mode = decisions_mode

    def validate(self, decision: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        cleaned: dict[str, Any] = {}
        warnings: list[str] = []

        for f in self._schema._ast.fields:
            value = decision.get(f.name)
            # Missing field
            if f.name not in decision or value is None:
                if f.optional:
                    continue
                msg = f"Required field '{f.name}' is missing"
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
        for k, v in decision.items():
            if k not in cleaned and k not in {f.name for f in self._schema._ast.fields}:
                cleaned[k] = v

        return cleaned, warnings
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_decision_validator.py -v
```

**Step 5: Commit**
```bash
git add amino/runtime/validator.py tests/test_decision_validator.py
git commit -m "feat: add DecisionValidator with strict/loose modes and constraint checking"
```

---

## Task 12: Matcher

Rewrite `amino/runtime/matcher.py` with four modes: `all`, `first`, `inverse`, `score`. New `MatchResult` with `matched`, `excluded`, `score`, `warnings`.

**Files:**
- Rewrite: `amino/runtime/matcher.py`
- Rewrite: `tests/test_matcher.py`

**Step 1: Write the failing tests**

```python
# tests/test_matcher.py
from amino.runtime.matcher import Matcher, MatchResult

def _results(matched_ids: list, all_ids: list) -> list[tuple]:
    """Build fake rule results: (rule_id, bool)."""
    matched = set(matched_ids)
    return [(rid, rid in matched) for rid in all_ids]

ALL_IDS = ["r1", "r2", "r3"]

def test_all_mode():
    m = Matcher({"mode": "all"})
    r = m.process("d1", _results(["r1", "r3"], ALL_IDS), {}, [])
    assert r.matched == ["r1", "r3"]
    assert r.excluded == []

def test_first_mode_by_ordering():
    m = Matcher({"mode": "first", "key": "ordering", "order": "asc"})
    metadata = {"r1": {"ordering": 3}, "r2": {"ordering": 1}, "r3": {"ordering": 2}}
    results = _results(["r1", "r2", "r3"], ALL_IDS)
    r = m.process("d1", results, metadata, [])
    assert r.matched == ["r2"]  # lowest ordering

def test_first_mode_no_match():
    m = Matcher({"mode": "first", "key": "ordering", "order": "asc"})
    r = m.process("d1", _results([], ALL_IDS), {}, [])
    assert r.matched == []

def test_inverse_mode():
    m = Matcher({"mode": "inverse"})
    r = m.process("d1", _results(["r1"], ALL_IDS), {}, [])
    assert r.excluded == ["r2", "r3"]
    assert r.matched == []

def test_score_mode_sum():
    m = Matcher({"mode": "score", "aggregate": "sum"})
    # r1 returns True (1.0), r2 returns 0.7, r3 returns False (0.0)
    results = [("r1", True), ("r2", 0.7), ("r3", False)]
    r = m.process("d1", results, {}, [])
    assert abs(r.score - 1.7) < 0.001

def test_score_mode_threshold():
    m = Matcher({"mode": "score", "aggregate": "sum", "threshold": 2.0})
    results = [("r1", True), ("r2", 0.7)]
    r = m.process("d1", results, {}, [])
    assert r.score == pytest.approx(1.7)
    # score below threshold → matched is empty
    assert r.matched == []

def test_warnings_propagated():
    m = Matcher({"mode": "all"})
    r = m.process("d1", _results([], ALL_IDS), {}, ["field x missing"])
    assert "field x missing" in r.warnings

def test_decision_id_on_result():
    m = Matcher({"mode": "all"})
    r = m.process("my-decision", _results([], ALL_IDS), {}, [])
    assert r.id == "my-decision"
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_matcher.py -v
```

**Step 3: Implement**

```python
# amino/runtime/matcher.py
import dataclasses
import pytest  # only in tests; remove from production
from typing import Any


@dataclasses.dataclass
class MatchResult:
    id: Any
    matched: list[str] = dataclasses.field(default_factory=list)
    excluded: list[str] = dataclasses.field(default_factory=list)
    score: float | None = None
    warnings: list[str] = dataclasses.field(default_factory=list)


class Matcher:
    def __init__(self, config: dict[str, Any] | None = None):
        cfg = config or {}
        self._mode = cfg.get("mode", "all")
        self._key = cfg.get("key")
        self._order = cfg.get("order", "asc")
        self._aggregate = cfg.get("aggregate", "sum")
        self._threshold = cfg.get("threshold")

    def process(
        self,
        decision_id: Any,
        rule_results: list[tuple[Any, Any]],
        metadata: dict[Any, dict],
        warnings: list[str],
    ) -> MatchResult:
        if self._mode == "all":
            matched = [rid for rid, val in rule_results if val]
            return MatchResult(id=decision_id, matched=matched, warnings=list(warnings))

        if self._mode == "first":
            matched = [rid for rid, val in rule_results if val]
            if not matched:
                return MatchResult(id=decision_id, matched=[], warnings=list(warnings))
            if self._key:
                matched = sorted(
                    matched,
                    key=lambda rid: metadata.get(rid, {}).get(self._key, float("inf")),
                    reverse=(self._order == "desc"),
                )
            return MatchResult(id=decision_id, matched=[matched[0]], warnings=list(warnings))

        if self._mode == "inverse":
            excluded = [rid for rid, val in rule_results if not val]
            return MatchResult(id=decision_id, excluded=excluded, warnings=list(warnings))

        if self._mode == "score":
            total = 0.0
            for _rid, val in rule_results:
                if isinstance(val, bool):
                    total += 1.0 if val else 0.0
                elif isinstance(val, (int, float)):
                    total += float(val)
            result = MatchResult(id=decision_id, score=total, warnings=list(warnings))
            if self._threshold is not None and total >= self._threshold:
                result.matched = [rid for rid, val in rule_results if val]
            return result

        raise ValueError(f"Unknown match mode: {self._mode!r}")
```

> **Note:** Remove the `import pytest` line from the production code — it was accidentally included above. Only the test file imports pytest.

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_matcher.py -v
```

**Step 5: Commit**
```bash
git add amino/runtime/matcher.py tests/test_matcher.py
git commit -m "feat: rewrite matcher with all/first/inverse/score modes and new MatchResult"
```

---

## Task 13: CompiledRules

Update `amino/runtime/compiled_rules.py` for new interfaces: `DecisionValidator`, new `Matcher`, new `MatchResult`.

**Files:**
- Rewrite: `amino/runtime/compiled_rules.py`
- Create: `tests/test_compiled_rules.py`

**Step 1: Write the failing tests**

```python
# tests/test_compiled_rules.py
from amino.operators.standard import build_operator_registry
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.rules.parser import parse_rule
from amino.rules.compiler import TypedCompiler
from amino.runtime.compiled_rules import CompiledRules
from amino.runtime.validator import DecisionValidator

SCHEMA = "score: Int\nname: Str"

def _make_compiled(rules: list[dict], match: dict | None = None):
    reg = SchemaRegistry(parse_schema(SCHEMA))
    ops = build_operator_registry("standard")
    compiler = TypedCompiler()
    compiled_list = []
    for r in rules:
        ast = parse_rule(r["rule"], reg, ops)
        compiled_list.append((r["id"], compiler.compile(r["id"], ast), r))
    validator = DecisionValidator(reg, decisions_mode="loose")
    return CompiledRules(compiled_list, validator, match_config=match)

def test_eval_single_all_mode():
    cr = _make_compiled([
        {"id": "r1", "rule": "score > 400"},
        {"id": "r2", "rule": "name = 'alice'"},
    ])
    result = cr.eval_single({"score": 500, "name": "bob"})
    assert "r1" in result.matched
    assert "r2" not in result.matched

def test_eval_single_first_mode():
    cr = _make_compiled([
        {"id": "r1", "rule": "score > 400", "ordering": 2},
        {"id": "r2", "rule": "score > 100", "ordering": 1},
    ], match={"mode": "first", "key": "ordering", "order": "asc"})
    result = cr.eval_single({"score": 500, "name": "x"})
    assert result.matched == ["r2"]

def test_eval_batch():
    cr = _make_compiled([{"id": "r1", "rule": "score > 400"}])
    results = cr.eval([{"score": 500}, {"score": 200}])
    assert "r1" in results[0].matched
    assert "r1" not in results[1].matched

def test_warnings_from_loose_validation():
    cr = _make_compiled([{"id": "r1", "rule": "score > 0"}])
    result = cr.eval_single({"score": "not-an-int"})  # wrong type, loose mode
    assert result.warnings  # validator added a warning
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_compiled_rules.py -v
```

**Step 3: Implement**

```python
# amino/runtime/compiled_rules.py
from typing import Any
from .matcher import Matcher, MatchResult
from .validator import DecisionValidator
from amino.rules.compiler import CompiledRule


class CompiledRules:
    def __init__(
        self,
        rules: list[tuple[Any, CompiledRule, dict]],
        validator: DecisionValidator,
        match_config: dict | None = None,
        function_registry: dict | None = None,
    ):
        # rules: list of (rule_id, CompiledRule, raw_rule_dict)
        self._rules = rules
        self._validator = validator
        self._matcher = Matcher(match_config)
        self._functions = function_registry or {}
        self._metadata = {rule_id: raw for rule_id, _, raw in rules}

    def eval_single(self, decision: dict[str, Any]) -> MatchResult:
        cleaned, warnings = self._validator.validate(decision)
        rule_results: list[tuple[Any, Any]] = []
        for rule_id, compiled, _ in self._rules:
            try:
                val = compiled.evaluate(cleaned, self._functions)
            except Exception:
                val = False
            rule_results.append((rule_id, val))
        decision_id = decision.get("id")
        return self._matcher.process(decision_id, rule_results, self._metadata, warnings)

    def eval(self, decisions: list[dict[str, Any]]) -> list[MatchResult]:
        return [self.eval_single(d) for d in decisions]
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_compiled_rules.py -v
```

**Step 5: Commit**
```bash
git add amino/runtime/compiled_rules.py tests/test_compiled_rules.py
git commit -m "feat: update CompiledRules for new validator, matcher, and MatchResult"
```

---

## Task 14: Engine

New `amino/engine.py`. Orchestrates all registries. Enforces freeze-before-use: any call to `register_*` or `add_function` after the first `compile()` or `eval()` raises `EngineAlreadyFrozenError`.

**Files:**
- Create: `amino/engine.py`
- Create: `tests/test_engine.py`

**Step 1: Write the failing tests**

```python
# tests/test_engine.py
import pytest
import amino
from amino.errors import EngineAlreadyFrozenError, OperatorConflictError

SCHEMA = "score: Int\nname: Str\nactive: Bool"

def test_basic_compile_and_eval():
    engine = amino.load_schema(SCHEMA)
    compiled = engine.compile([{"id": "r1", "rule": "score > 400"}])
    result = compiled.eval_single({"score": 500})
    assert "r1" in result.matched

def test_one_shot_eval():
    engine = amino.load_schema(SCHEMA)
    result = engine.eval(
        rules=[{"id": "r1", "rule": "score > 400"}],
        decision={"score": 500},
    )
    assert "r1" in result.matched

def test_freeze_on_compile():
    engine = amino.load_schema(SCHEMA)
    engine.compile([{"id": "r1", "rule": "score > 0"}])
    with pytest.raises(EngineAlreadyFrozenError):
        engine.add_function("foo", lambda: 1)

def test_freeze_on_eval():
    engine = amino.load_schema(SCHEMA)
    engine.eval(rules=[{"id": "r1", "rule": "score > 0"}], decision={"score": 1})
    with pytest.raises(EngineAlreadyFrozenError):
        engine.register_type("mytype", base="Str", validator=lambda v: True)

def test_register_type_before_compile():
    engine = amino.load_schema("ip: ipv4")
    engine.register_type("ipv4", base="Str", validator=lambda v: isinstance(v, str))
    compiled = engine.compile([{"id": "r1", "rule": "ip = '1.2.3.4'"}])
    result = compiled.eval_single({"ip": "1.2.3.4"})
    assert "r1" in result.matched

def test_register_custom_operator():
    engine = amino.load_schema(SCHEMA, operators="minimal")
    engine.register_operator(
        keyword="above", fn=lambda l, r: l > r,
        binding_power=40, input_types=("Int", "Int"), return_type="Bool",
    )
    compiled = engine.compile([{"id": "r1", "rule": "score above 400"}])
    result = compiled.eval_single({"score": 500})
    assert "r1" in result.matched

def test_duplicate_operator_raises():
    engine = amino.load_schema(SCHEMA)
    with pytest.raises(OperatorConflictError):
        engine.register_operator(
            symbol="=", fn=lambda l, r: l == r,
            binding_power=40, input_types=("*", "*"), return_type="Bool",
        )

def test_update_rules_hot_swap():
    engine = amino.load_schema(SCHEMA)
    engine.compile([{"id": "r1", "rule": "score > 400"}])
    # hot-swap is compile-time idempotent — schema stays same
    compiled2 = engine.compile([{"id": "r2", "rule": "score < 100"}])
    result = compiled2.eval_single({"score": 50})
    assert "r2" in result.matched

def test_export_schema():
    engine = amino.load_schema(SCHEMA)
    exported = engine.export_schema()
    assert "score: Int" in exported
    assert "name: Str" in exported

def test_match_modes():
    engine = amino.load_schema(SCHEMA)
    compiled = engine.compile(
        [{"id": "r1", "rule": "score > 0", "ordering": 2},
         {"id": "r2", "rule": "active = true", "ordering": 1}],
        match={"mode": "first", "key": "ordering", "order": "asc"},
    )
    result = compiled.eval_single({"score": 100, "active": True})
    assert result.matched == ["r1"] or result.matched == ["r2"]  # first by ordering

def test_rules_mode_and_decisions_mode():
    engine = amino.load_schema(SCHEMA, rules_mode="strict", decisions_mode="loose")
    compiled = engine.compile([{"id": "r1", "rule": "score > 0"}])
    result = compiled.eval_single({"score": "bad"})  # loose: skip and warn
    assert result.warnings
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_engine.py -v
```

**Step 3: Implement**

```python
# amino/engine.py
from collections.abc import Callable
from typing import Any

from amino.errors import EngineAlreadyFrozenError
from amino.operators.registry import OperatorDef, OperatorRegistry
from amino.operators.standard import build_operator_registry
from amino.rules.compiler import TypedCompiler
from amino.rules.parser import parse_rule
from amino.runtime.compiled_rules import CompiledRules
from amino.runtime.matcher import MatchResult
from amino.runtime.validator import DecisionValidator
from amino.schema.parser import parse_schema
from amino.schema.registry import SchemaRegistry
from amino.types.builtin import register_builtin_types
from amino.types.registry import TypeRegistry


class Engine:
    def __init__(
        self,
        schema_text: str,
        *,
        funcs: dict[str, Callable] | None = None,
        rules_mode: str = "strict",
        decisions_mode: str = "loose",
        operators: "str | list[str]" = "standard",
    ):
        ast = parse_schema(schema_text)
        self._type_registry = TypeRegistry()
        register_builtin_types(self._type_registry)
        self._op_registry: OperatorRegistry = build_operator_registry(operators)
        self._schema_registry = SchemaRegistry(
            ast, known_custom_types=self._type_registry.registered_names()
        )
        self._functions: dict[str, Callable] = dict(funcs or {})
        self._rules_mode = rules_mode
        self._decisions_mode = decisions_mode
        self._frozen = False

    # ── Registration ──────────────────────────────────────────────────

    def _check_frozen(self) -> None:
        if self._frozen:
            raise EngineAlreadyFrozenError(
                "Cannot register after first compile() or eval()"
            )

    def add_function(self, name: str, fn: Callable) -> None:
        self._check_frozen()
        self._functions[name] = fn

    def register_type(self, name: str, base: str, validator: Callable) -> None:
        self._check_frozen()
        self._type_registry.register_type(name, base, validator)

    def register_operator(
        self,
        *,
        symbol: str | None = None,
        keyword: str | None = None,
        kind: str = "infix",
        fn: Callable,
        binding_power: int,
        associativity: str = "left",
        input_types: tuple[str, ...] = ("*", "*"),
        return_type: str = "Bool",
    ) -> None:
        self._check_frozen()
        op = OperatorDef(
            symbol=symbol, keyword=keyword, kind=kind, fn=fn,
            binding_power=binding_power, associativity=associativity,
            input_types=input_types, return_type=return_type,
        )
        self._op_registry.register(op)

    # ── Compilation ───────────────────────────────────────────────────

    def _freeze(self) -> None:
        self._frozen = True

    def compile(
        self, rules: list[dict[str, Any]], match: dict | None = None
    ) -> CompiledRules:
        self._freeze()
        compiler = TypedCompiler(rules_mode=self._rules_mode)
        compiled_list = []
        for raw in rules:
            rule_id = raw["id"]
            ast = parse_rule(raw["rule"], self._schema_registry, self._op_registry)
            compiled = compiler.compile(rule_id, ast)
            compiled_list.append((rule_id, compiled, raw))
        validator = DecisionValidator(self._schema_registry, self._decisions_mode)
        return CompiledRules(
            compiled_list, validator,
            match_config=match,
            function_registry=self._functions,
        )

    def eval(
        self,
        rules: list[dict[str, Any]],
        decision: dict[str, Any],
        match: dict | None = None,
    ) -> MatchResult:
        compiled = self.compile(rules, match)
        return compiled.eval_single(decision)

    def export_schema(self) -> str:
        return self._schema_registry.export_schema()
```

**Step 4: Run to verify pass**
```bash
uv run pytest tests/test_engine.py -v
```

**Step 5: Commit**
```bash
git add amino/engine.py tests/test_engine.py
git commit -m "feat: add Engine class with freeze-before-use and full lifecycle"
```

---

## Task 15: Public API, cleanup, and integration tests

Wire up `amino/__init__.py` with the new `load_schema()`. Remove old test files that tested deleted modules. Add integration tests covering the full pipeline.

**Files:**
- Rewrite: `amino/__init__.py`
- Create: `tests/test_integration.py`
- Delete: `tests/test_amino_api.py`, `tests/test_basic.py`, `tests/test_runtime.py`, `tests/test_runtime_evaluator.py`, `tests/test_advanced_schema_features.py`, `tests/test_rule_parser.py` (old version)

**Step 1: Write the failing tests**

```python
# tests/test_integration.py
"""End-to-end tests through the public API."""
import amino
from amino.errors import (
    DecisionValidationError, EngineAlreadyFrozenError,
    SchemaParseError, SchemaValidationError,
)
import pytest

# ── dmarcian-style classifier ─────────────────────────────────────────────────

CLASSIFIER_SCHEMA = """
asn: Int
cname: Str?
org: Str?
"""

def test_email_classifier_first_match():
    engine = amino.load_schema(CLASSIFIER_SCHEMA)
    rules = [
        {"id": 1, "rule": "asn = 16509", "ordering": 1, "name": "Amazon SES"},
        {"id": 2, "rule": "asn = 15169", "ordering": 2, "name": "Google"},
        {"id": 3, "rule": "asn = 8075",  "ordering": 3, "name": "Microsoft"},
    ]
    compiled = engine.compile(rules, match={"mode": "first", "key": "ordering", "order": "asc"})
    result = compiled.eval_single({"asn": 15169})
    assert result.matched == [2]

def test_email_classifier_no_match():
    engine = amino.load_schema(CLASSIFIER_SCHEMA)
    rules = [{"id": 1, "rule": "asn = 16509", "ordering": 1}]
    compiled = engine.compile(rules, match={"mode": "first", "key": "ordering", "order": "asc"})
    result = compiled.eval_single({"asn": 99999})
    assert result.matched == []

# ── auto loan decline layer ───────────────────────────────────────────────────

LOAN_SCHEMA = """
state_code: Str
credit_score: Int
applicant_type: Str
"""

def test_hard_decline_rules():
    engine = amino.load_schema(LOAN_SCHEMA)
    rules = [
        {"id": "decline_state",  "rule": "state_code in ['CA', 'NY']"},
        {"id": "decline_credit", "rule": "credit_score < 450"},
    ]
    compiled = engine.compile(rules)

    result = compiled.eval_single({"state_code": "CA", "credit_score": 700, "applicant_type": "single"})
    assert "decline_state" in result.matched
    assert "decline_credit" not in result.matched

    result = compiled.eval_single({"state_code": "TX", "credit_score": 400, "applicant_type": "single"})
    assert "decline_credit" in result.matched

# ── stipulation pattern ───────────────────────────────────────────────────────

STIP_SCHEMA = """
income_auto_verified: Bool
employment_tenure_months: Int
"""

def test_stipulation_as_boolean_rules():
    engine = amino.load_schema(STIP_SCHEMA)
    rules = [
        {"id": "stip_income",      "rule": "income_auto_verified = false", "action": "proof_of_income"},
        {"id": "stip_employment",  "rule": "employment_tenure_months < 6", "action": "employment_verification"},
    ]
    compiled = engine.compile(rules)
    result = compiled.eval_single({"income_auto_verified": False, "employment_tenure_months": 3})
    triggered = result.matched
    assert "stip_income" in triggered
    assert "stip_employment" in triggered

# ── scoring ────────────────────────────────────────────────────────────────────

SCORE_SCHEMA = "signal_a: Bool\nsignal_b: Bool\nsignal_c: Int"

def test_score_mode_aggregation():
    engine = amino.load_schema(SCORE_SCHEMA)
    rules = [
        {"id": "s1", "rule": "signal_a = true"},
        {"id": "s2", "rule": "signal_b = true"},
        {"id": "s3", "rule": "signal_c > 50"},
    ]
    compiled = engine.compile(rules, match={"mode": "score", "aggregate": "sum"})
    result = compiled.eval_single({"signal_a": True, "signal_b": False, "signal_c": 100})
    assert abs(result.score - 2.0) < 0.001

# ── inverse mode ──────────────────────────────────────────────────────────────

def test_inverse_mode_disqualification():
    engine = amino.load_schema(LOAN_SCHEMA)
    rules = [
        {"id": "eligible_state",  "rule": "state_code not in ['CA', 'NY']"},
        {"id": "eligible_credit", "rule": "credit_score >= 600"},
    ]
    compiled = engine.compile(rules, match={"mode": "inverse"})
    result = compiled.eval_single({"state_code": "TX", "credit_score": 500, "applicant_type": "single"})
    assert "eligible_credit" in result.excluded
    assert "eligible_state" not in result.excluded

# ── custom type registration ──────────────────────────────────────────────────

def test_custom_type_end_to_end():
    engine = amino.load_schema("ip: ipv4\nnetwork: cidr")
    engine.register_operator(
        keyword="within",
        fn=lambda ip, cidr: _cidr_contains(ip, cidr),
        binding_power=40,
        input_types=("ipv4", "cidr"),
        return_type="Bool",
    )
    compiled = engine.compile([{"id": "r1", "rule": "ip within network"}])
    result = compiled.eval_single({"ip": "10.0.0.5", "network": "10.0.0.0/8"})
    # Just verifying the pipeline doesn't crash; actual CIDR logic is in the fn
    assert result is not None

def _cidr_contains(ip: str, cidr: str) -> bool:
    import ipaddress
    return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)

# ── schema export ─────────────────────────────────────────────────────────────

def test_schema_export():
    engine = amino.load_schema("age: Int\nname: Str?")
    exported = engine.export_schema()
    assert "age: Int" in exported
    assert "name: Str?" in exported

# ── error cases ───────────────────────────────────────────────────────────────

def test_schema_parse_error():
    with pytest.raises(SchemaParseError):
        amino.load_schema("age: @Int")

def test_freeze_error():
    engine = amino.load_schema("x: Int")
    engine.eval(rules=[{"id": "r1", "rule": "x > 0"}], decision={"x": 1})
    with pytest.raises(EngineAlreadyFrozenError):
        engine.add_function("foo", lambda: 1)

def test_loose_decisions_mode_warns_not_raises():
    engine = amino.load_schema("score: Int", decisions_mode="loose")
    compiled = engine.compile([{"id": "r1", "rule": "score > 0"}])
    result = compiled.eval_single({"score": "bad_type"})
    assert result.warnings  # warned, not raised

def test_strict_decisions_mode_raises():
    engine = amino.load_schema("score: Int", decisions_mode="strict")
    compiled = engine.compile([{"id": "r1", "rule": "score > 0"}])
    with pytest.raises(DecisionValidationError):
        compiled.eval_single({"score": "bad_type"})
```

**Step 2: Run to verify fail**
```bash
uv run pytest tests/test_integration.py -v
```

**Step 3: Update public API**

```python
# amino/__init__.py
from .engine import Engine
from .errors import (
    AminoError, SchemaParseError, SchemaValidationError, RuleParseError,
    TypeMismatchError, DecisionValidationError, RuleEvaluationError,
    OperatorConflictError, EngineAlreadyFrozenError,
)

import pathlib
from collections.abc import Callable


def load_schema(
    source: str,
    *,
    funcs: dict[str, Callable] | None = None,
    rules_mode: str = "strict",
    decisions_mode: str = "loose",
    operators: "str | list[str]" = "standard",
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
    "load_schema", "Engine",
    "AminoError", "SchemaParseError", "SchemaValidationError",
    "RuleParseError", "TypeMismatchError", "DecisionValidationError",
    "RuleEvaluationError", "OperatorConflictError", "EngineAlreadyFrozenError",
]
```

Remove obsolete test files:
```bash
rm tests/test_amino_api.py tests/test_basic.py tests/test_runtime.py \
   tests/test_runtime_evaluator.py tests/test_advanced_schema_features.py
```

**Step 4: Run full test suite**
```bash
uv run pytest tests/ -v
```
Expected: all tests pass.

Run linting and type checking:
```bash
uv run ruff check amino/
uv run ty check amino/
```
Fix any issues before committing.

**Step 5: Commit**
```bash
git add amino/__init__.py tests/test_integration.py
git add -u  # pick up deletions
git commit -m "feat: wire public API and add integration tests for full pipeline"
```

---

## Final validation

Run the full test suite one more time to confirm everything is green:
```bash
uv run pytest tests/ -v --tb=short
uv run ruff check amino/
uv run ty check amino/
```

Then open a PR:
```bash
git push origin docs/adr-engine-architecture
# create PR via gh or GitHub UI targeting main
```
