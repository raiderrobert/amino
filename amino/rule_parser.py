import dataclasses
import enum
import regex

RESERVED_NAMES = ['and', 'or']  # all casing variations of these are reserved

whitespace = regex.compile(r"[\s]+")
name = regex.compile(r"[A-Za-z_]+")
number_literal = regex.compile(r"[\d]+")
string_literal = regex.compile(r"'[^']*'")
symbol = regex.compile("[^a-zA-Z0-9\\s'\"]+")


class TokenType(enum.Enum):
    whitespace = enum.auto()
    name = enum.auto()
    number_literal = enum.auto()
    string_literal = enum.auto()
    symbol = enum.auto()


token_map = {
    whitespace: TokenType.whitespace,
    number_literal: TokenType.number_literal,
    symbol: TokenType.symbol,
    string_literal: TokenType.string_literal,
    name: TokenType.name,
}


@dataclasses.dataclass
class Token:
    value: str
    token_type: TokenType


def _tokenizer(target: str) -> list[str]:
    tokens: list = []
    pos = 0
    while len(target) > 0:
        for pattern, token_type in token_map.items():
            match_obj = pattern.match(target)
            if match_obj is not None:
                value = match_obj.group(0)
                if token_type is not token_type.whitespace:
                    tokens.append(Token(value, token_type))
                pos = match_obj.end()
                target = target[pos:]
                break
        else:
            raise Exception(f'Unexpected characters at {target[pos:]}')
    return tokens
