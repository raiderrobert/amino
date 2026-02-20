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
