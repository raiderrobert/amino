import dataclasses
import enum
from typing import Optional

import regex

from amino.schema_parser import Names
from amino.schema_parser import SchemaType

whitespace = regex.compile(r"[\s]+")
name = regex.compile(r"[A-Za-z_]+")
parenthesis_open = regex.compile(r"[(]+")
parenthesis_close = regex.compile(r"[)]+")
number_literal = regex.compile(r"[\d]+")
string_literal = regex.compile(r"'[^']*'")
symbol = regex.compile("[^a-zA-Z0-9\\s'\"]+")


class TokenType(enum.Enum):
    whitespace = enum.auto()
    name = enum.auto()
    number_literal = enum.auto()
    string_literal = enum.auto()
    symbol = enum.auto()
    parenthesis_open = enum.auto()
    parenthesis_close = enum.auto()


token_map = {
    parenthesis_open: TokenType.parenthesis_open,
    parenthesis_close: TokenType.parenthesis_close,
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


@dataclasses.dataclass
class Func:
    name: str
    return_type: SchemaType
    arity: int


@dataclasses.dataclass
class Node:
    parent: Optional['Node']
    name: Func | str
    arguments: list

def builtin_funcs():
    funcs = [
        Func('paren', SchemaType.any, 1),
        Func('and', SchemaType.bool, 2),
        Func('or', SchemaType.bool, 2),
        Func('not', SchemaType.bool, 1),
        Func('=', SchemaType.bool, 2),
        Func('<', SchemaType.bool, 2),
        Func('>', SchemaType.bool, 2),
        Func('>=', SchemaType.bool, 2),
        Func('>=', SchemaType.bool, 2),
    ]
    return {'funcs': funcs, 'func_names': [ x.name for x in funcs]}


def parse_rule(rule, schema: list[Names]):
    tokens = _tokenizer(rule)
    func_tree = Node(parent=None, func='root', arguments=[])

    while len(tokens) > 0:
        match tokens:
            case [
                Token(value_1, TokenType.name | TokenType.string_literal | TokenType.number_literal),
                Token(infix_operator, TokenType.symbol | TokenType.name),
                Token(_type, TokenType.name | TokenType.string_literal | TokenType.number_literal),
                *remainder
            ]:

                pass
            case _:
                raise Exception(f'Unexpected remainder {tokens}')

    return func_tree
