import pytest
from amino.rule_parser import _tokenizer, Token, TokenType


@pytest.mark.parametrize(
    "test_input,expected,exception",
    [
        ("a > b", [Token("a", TokenType.name), Token(">", TokenType.symbol), Token("b", TokenType.name)], False),
        ("a > 1", [Token("a", TokenType.name), Token(">", TokenType.symbol), Token("1", TokenType.number_literal)], False),
        ("a < b and c > a",
         [Token("a", TokenType.name),
          Token("<", TokenType.symbol),
          Token("b", TokenType.name),
          Token("and", TokenType.name),
          Token("c", TokenType.name),
          Token(">", TokenType.symbol),
          Token("a", TokenType.name),
          ], False),
    ],
)
def test_tokenizer(test_input, expected, exception):
    if exception:
        with pytest.raises(Exception) as excinfo:
            assert str(excinfo.value) == expected
    else:
        assert _tokenizer(test_input) == expected
