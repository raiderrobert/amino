import pytest
from amino.schema_parser import parse_schema, Names, SchemaType


@pytest.mark.parametrize(
    "test_input,expected,exception",
    [
        ("foo:int", [Names("foo", name_type=SchemaType.int)], False),
        (
            """
            foo: int
            bar: str
            baz: bool
            bat: any
            """,
            [
                Names("foo", name_type=SchemaType.int),
                Names("bar", name_type=SchemaType.str),
                Names("baz", name_type=SchemaType.bool),
                Names("bat", name_type=SchemaType.any),
            ],
            False,
        ),
        (
            """
            bat: any
            blargh: boo
            """,
            "Unexpected type boo",
            True,
        ),
    ],
)
def test_good(test_input, expected, exception):
    with pytest.raises(Exception) as excinfo:
        output = parse_schema(test_input)
        if exception:
            assert str(excinfo.value) == expected
        else:
            assert output == expected
