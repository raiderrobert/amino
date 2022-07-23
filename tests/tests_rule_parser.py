import pytest
from amino.rule_parser import NodeType, Parser, GT, Literal, Name
from amino.schema_parser import parse_schema, SchemaType

#
# @pytest.mark.parametrize(
#     "test_input,expected,exception",
#     [
#         (
#             "a > b",
#             [Token("a", TokenType.name, None), Token(">", TokenType.symbol, None), Token("b", TokenType.name, None)],
#             False,
#         ),
#         (
#             "a > 1",
#             [
#                 Token("a", TokenType.name, None),
#                 Token(">", TokenType.symbol, None),
#                 Token("1", TokenType.int_literal, None),
#             ],
#             False,
#         ),
#         (
#             "a < b and c > a",
#             [
#                 Token("a", TokenType.name, None),
#                 Token("<", TokenType.symbol, None),
#                 Token("b", TokenType.name, None),
#                 Token("and", TokenType.name, None),
#                 Token("c", TokenType.name, None),
#                 Token(">", TokenType.symbol, None),
#                 Token("a", TokenType.name, None),
#             ],
#             False,
#         ),
#     ],
# )
# def test_tokenizer(test_input, expected, exception):
#     if exception:
#         with pytest.raises(Exception) as excinfo:
#             assert str(excinfo.value) == expected
#     else:
#         assert _tokenizer(test_input) == expected


@pytest.mark.parametrize(
    "test_schema,test_rule,expected,exception",
    [
        (
            """
            a: int
            b: int
            """,
            "2 > 1",
            NodeType(type=GT, arguments=[Literal("2", SchemaType.int), Literal("1", SchemaType.int)], parent=None),
            False,
        ),
        (
            """
            a: int
            b: int
            """,
            "a > 1",
            NodeType(type=GT, arguments=[Name("a", SchemaType.int), Literal("1", SchemaType.int)], parent=None),
            False,
        ),
        (
            """
            a: int
            b: int
            """,
            "1 > a",
            NodeType(type=GT, arguments=[Literal("1", SchemaType.int), Name("a", SchemaType.int)], parent=None),
            False,
        ),
        # (
        #         """
        #         a: int
        #         b: int
        #         """,
        #         "a > b and b > 0",
        #         NodeType(
        #             name="root",
        #             arguments=[
        #                 Node(
        #                     name=Func(">", PositionType.infix, SchemaType.bool, 2),
        #                     arguments=[["a", SchemaType.int], ["b", SchemaType.int]],
        #                 )
        #             ],
        #         ),
        #         False,
        # ),
    ],
)
def test_parse_rule(test_schema, test_rule, expected, exception):
    if exception:
        with pytest.raises(Exception) as excinfo:
            assert str(excinfo.value) == expected
    else:
        parsed_schema = parse_schema(test_schema)
        assert Parser(test_rule, parsed_schema).parse_all() == expected
