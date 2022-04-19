import pytest
from amino.rule_parser import _tokenizer, Token, TokenType, parse_rule, Node, Func, PositionType
from amino.schema_parser import parse_schema, SchemaType


@pytest.mark.parametrize(
    "test_input,expected,exception",
    [
        (
            "a > b",
            [Token("a", TokenType.name, None), Token(">", TokenType.symbol, None), Token("b", TokenType.name, None)],
            False,
        ),
        (
            "a > 1",
            [
                Token("a", TokenType.name, None),
                Token(">", TokenType.symbol, None),
                Token("1", TokenType.number_literal, None),
            ],
            False,
        ),
        (
            "a < b and c > a",
            [
                Token("a", TokenType.name, None),
                Token("<", TokenType.symbol, None),
                Token("b", TokenType.name, None),
                Token("and", TokenType.name, None),
                Token("c", TokenType.name, None),
                Token(">", TokenType.symbol, None),
                Token("a", TokenType.name, None),
            ],
            False,
        ),
    ],
)
def test_tokenizer(test_input, expected, exception):
    if exception:
        with pytest.raises(Exception) as excinfo:
            assert str(excinfo.value) == expected
    else:
        assert _tokenizer(test_input) == expected


@pytest.mark.parametrize(
    "test_schema,test_rule,expected,exception",
    [
        (
            """
            a: int
            b: int
            """,
            "a > b",
            Node(
                name="root",
                arguments=[
                    Node(
                        name=Func(">", PositionType.infix, SchemaType.bool, 2),
                        arguments=[["a", SchemaType.int], ["b", SchemaType.int]],
                    )
                ],
            ),
            False,
        ),
    ],
)
def test_parse_rule(test_schema, test_rule, expected, exception):
    if exception:
        with pytest.raises(Exception) as excinfo:
            assert str(excinfo.value) == expected
    else:
        parsed_schema = parse_schema(test_schema)
        assert parse_rule(test_rule, parsed_schema) == expected
