import pytest

from amino.schema.parser import parse_schema
from amino.schema.types import SchemaType
from amino.utils.errors import SchemaParseError


@pytest.mark.parametrize(
    "test_input,expected_fields,should_raise,expected_error",
    [
        ("foo: int", [("foo", SchemaType.int)], False, None),
        (
            """
            foo: int
            bar: str
            baz: bool
            bat: any
            """,
            [
                ("foo", SchemaType.int),
                ("bar", SchemaType.str),
                ("baz", SchemaType.bool),
                ("bat", SchemaType.any),
            ],
            False,
            None,
        ),
        (
            """
            bat: any
            blargh: boo
            """,
            [
                ("bat", SchemaType.any),
                ("blargh", SchemaType.custom),
            ],
            False,
            None,
        ),
        (
            "amount: float",
            [("amount", SchemaType.float)],
            False,
            None,
        ),
        (
            "email: str {format: email}",
            [("email", SchemaType.str)],
            False,
            None,
        ),
    ],
)
def test_schema_parsing(test_input, expected_fields, should_raise, expected_error):
    """Test schema parsing with new architecture."""
    if should_raise:
        with pytest.raises(SchemaParseError) as excinfo:
            parse_schema(test_input)
        assert expected_error in str(excinfo.value)
    else:
        ast = parse_schema(test_input)
        assert len(ast.fields) == len(expected_fields)

        for i, (expected_name, expected_type) in enumerate(expected_fields):
            field = ast.fields[i]
            assert field.name == expected_name
            assert field.field_type == expected_type


def test_schema_with_constraints():
    """Test schema parsing with constraints."""
    schema_content = "age: int {min: 18, max: 120}"
    ast = parse_schema(schema_content)

    assert len(ast.fields) == 1
    field = ast.fields[0]
    assert field.name == "age"
    assert field.field_type == SchemaType.int
    assert field.constraints["min"] == 18
    assert field.constraints["max"] == 120


def test_schema_with_optional_fields():
    """Test schema parsing with optional fields."""
    schema_content = "name: str\nage: int?"
    ast = parse_schema(schema_content)

    assert len(ast.fields) == 2
    assert ast.fields[0].name == "name"
    assert not ast.fields[0].optional
    assert ast.fields[1].name == "age"
    assert ast.fields[1].optional


def test_schema_with_structs():
    """Test schema parsing with struct definitions."""
    schema_content = """
    struct person {
        name: str,
        age: int
    }
    """
    ast = parse_schema(schema_content)

    assert len(ast.structs) == 1
    struct = ast.structs[0]
    assert struct.name == "person"
    assert len(struct.fields) == 2
    assert struct.fields[0].name == "name"
    assert struct.fields[1].name == "age"


def test_schema_with_constants():
    """Test schema parsing with constants."""
    schema_content = "MAX_AGE: int = 120\nname: str"
    ast = parse_schema(schema_content)

    assert "MAX_AGE" in ast.constants
    assert ast.constants["MAX_AGE"] == 120
    assert len(ast.fields) == 1


def test_schema_with_comments():
    """Test schema parsing with comments."""
    schema_content = """
    # This is a comment
    name: str  # Another comment
    age: int
    """
    ast = parse_schema(schema_content)

    assert len(ast.fields) == 2
    assert ast.fields[0].name == "name"
    assert ast.fields[1].name == "age"
