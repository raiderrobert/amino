import pytest
from amino.schema_parser import parse_schema, Names, SchemaType


@pytest.mark.parametrize(
    "test_input,expected,exception",
    [
        ("foo:int", [Names("foo", _type=SchemaType.int)], False),
        (
            """
            foo:int
            bar: str
            baz: bool
            bat: any
            """,
            [
                Names("foo", _type=SchemaType.int),
                Names("bar", _type=SchemaType.str),
                Names("baz", _type=SchemaType.bool),
                Names("bat", _type=SchemaType.any),
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

    if exception:
        with pytest.raises(Exception) as excinfo:
            assert str(excinfo.value) == expected
    else:
        assert parse_schema(test_input) == expected
