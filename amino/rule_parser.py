import dataclasses
import enum
from typing import Optional

import regex

from amino.schema_parser import Names
from amino.schema_parser import SchemaType

whitespace = regex.compile(r"[\s]+")
name_token = regex.compile(r"[A-Za-z_]+")
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
    name_token: TokenType.name,
}


@dataclasses.dataclass
class Token:
    value: str
    token_type: TokenType


def _tokenizer(target: str) -> list[Token]:
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


class PositionType(enum.Enum):
    prefix = enum.auto()
    infix = enum.auto()
    postfix = enum.auto()


@dataclasses.dataclass
class Func:
    name: str
    position_type: PositionType
    return_type: SchemaType
    arity: int


@dataclasses.dataclass
class Node:
    parent: Optional['Node']
    name: Func | str
    arguments: list


def builtin_funcs():
    funcs = [
        Func('paren', PositionType.prefix, SchemaType.any, 1),
        Func('and', PositionType.infix, SchemaType.bool, 2),
        Func('or', PositionType.infix, SchemaType.bool, 2),
        Func('not', PositionType.prefix, SchemaType.bool, 1),
        Func('=', PositionType.infix, SchemaType.bool, 2),
        Func('<', PositionType.infix, SchemaType.bool, 2),
        Func('>', PositionType.infix, SchemaType.bool, 2),
        Func('>=', PositionType.infix, SchemaType.bool, 2),
        Func('>=', PositionType.infix, SchemaType.bool, 2),
    ]

    func_types = {_t: [] for _t in PositionType}
    for f in funcs:
        func_types[f.position_type].append(f.name)

    return {f.name: f for f in funcs}, func_types


def parse_rule(rule, schema: list[Names]):
    tokens = _tokenizer(rule)
    func_tree = Node(parent=None, name='root', arguments=[])
    funcs, func_types = builtin_funcs()

    while len(tokens) > 0:
        match tokens:
            case [
                Token(value_1, TokenType.name | TokenType.string_literal | TokenType.number_literal),
                Token(infix_operator, TokenType.symbol | TokenType.name),
                Token(_type, TokenType.name | TokenType.string_literal | TokenType.number_literal),
                *remainder
            ] if infix_operator in func_types[PositionType.infix]:
                name = funcs[infix_operator]

                Node(parent=func_tree, name=name, arguments=[value_1])

                pass
            case _:
                raise Exception(f'Unexpected remainder {tokens}')

    return func_tree
