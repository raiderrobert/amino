import dataclasses
import enum
from typing import Optional

import regex

from amino.schema_parser import Schema, SchemaType

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

token_return_type_map = {
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
    schema_type: SchemaType | None


def _tokenizer(target: str, schema: Schema | None = None) -> list[Token]:
    tokens: list = []
    pos = 0
    while len(target) > 0:
        for pattern, token_type in token_map.items():
            match_obj = pattern.match(target)
            if match_obj is not None:
                value = match_obj.group(0)
                if token_type is not token_type.whitespace:
                    schema_type = None
                    if schema:
                        match token_type:
                            case TokenType.name:
                                schema_type = schema.get_type(value)
                            case TokenType.string_literal:
                                schema_type = SchemaType.str
                            case TokenType.number_literal:
                                schema_type = SchemaType.int

                    tokens.append(Token(value, token_type, schema_type))
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


def parse_rule(rule, schema: Schema):
    tokens = _tokenizer(rule, schema)
    func_tree = Node(name='root', arguments=[])
    funcs, func_types = builtin_funcs()

    for _ in tokens:
        match tokens:
            case [
                Token(t1, TokenType.name | TokenType.string_literal | TokenType.number_literal, t1_type),
                Token(infix_operator, infix_type),
                Token(t2, TokenType.name | TokenType.string_literal | TokenType.number_literal, t2_type),
                *tokens
            ] if infix_operator in func_types[PositionType.infix] and infix_type in (TokenType.symbol, TokenType.name):
                name = funcs[infix_operator]
                func_tree.arguments.append(Node(name=name, arguments=[[t1, t1_type],[t2,t2_type]]))
            case []:
                break
            case _:
                raise Exception(f'Unexpected remainder {tokens}')

    return func_tree
