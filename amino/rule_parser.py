import dataclasses
import enum
import typing

import regex

from amino.schema_parser import Schema, SchemaType

whitespace_regex = regex.compile(r"[\s]+")
name_regex = regex.compile(r"[A-Za-z_]+")
parenthesis_open_regex = regex.compile(r"[(]+")
parenthesis_close_regex = regex.compile(r"[)]+")
int_literal_regex = regex.compile(r"[\d]+")
string_literal_regex = regex.compile(r"'[^']*'")
symbol_regex = regex.compile("[^a-zA-Z0-9\\s'\"]+")


class TokenType(enum.Enum):
    whitespace = enum.auto()
    name = enum.auto()
    int_literal = enum.auto()
    string_literal = enum.auto()
    symbol = enum.auto()
    parenthesis_open = enum.auto()
    parenthesis_close = enum.auto()


token_map = {
    parenthesis_open_regex: TokenType.parenthesis_open,
    parenthesis_close_regex: TokenType.parenthesis_close,
    whitespace_regex: TokenType.whitespace,
    int_literal_regex: TokenType.int_literal,
    symbol_regex: TokenType.symbol,
    string_literal_regex: TokenType.string_literal,
    name_regex: TokenType.name,
}


token_return_type_map = {
    parenthesis_open_regex: TokenType.parenthesis_open,
    parenthesis_close_regex: TokenType.parenthesis_close,
    whitespace_regex: TokenType.whitespace,
    int_literal_regex: TokenType.int_literal,
    symbol_regex: TokenType.symbol,
    string_literal_regex: TokenType.string_literal,
    name_regex: TokenType.name,
}


@dataclasses.dataclass
class Token:
    value: str
    token_type: TokenType
    pos_start: int
    pos_end: int


class PositionType(enum.Enum):
    prefix = enum.auto()
    infix = enum.auto()
    postfix = enum.auto()


@dataclasses.dataclass
class Keyword:
    name: str
    position_type: PositionType
    return_type: SchemaType
    arity: int


@dataclasses.dataclass
class Name:
    name: str
    return_type: SchemaType


@dataclasses.dataclass
class Paren:
    pass


@dataclasses.dataclass
class Symbol:
    token: str
    position_type: PositionType
    return_type: SchemaType
    arity: int


@dataclasses.dataclass
class Literal:
    value: str
    type: SchemaType


@dataclasses.dataclass
class LookupSymbol:
    token: dict[str, Symbol]
    position_type: dict[PositionType, Symbol]


EQ = Symbol("=", PositionType.infix, SchemaType.bool, 2)
GT = Symbol(">", PositionType.infix, SchemaType.bool, 2)
LT = Symbol("<", PositionType.infix, SchemaType.bool, 2)
GTE = Symbol(">=", PositionType.infix, SchemaType.bool, 2)
LTE = Symbol("<=", PositionType.infix, SchemaType.bool, 2)


def builtin_symbols() -> LookupSymbol:
    funcs = [
        EQ,
        GT,
        LT,
        GTE,
        LTE,
    ]

    func_types = {_t: [] for _t in PositionType}
    for f in funcs:
        func_types[f.position_type].append(f.token)

    return LookupSymbol({f.token: f for f in funcs}, func_types)


@dataclasses.dataclass
class LookupKeyword:
    name: dict[str, Keyword]
    position_type: dict[PositionType, Keyword]

    def get_type(self, name: str) -> Keyword:
        return self.name[name]


AND = Keyword("and", PositionType.infix, SchemaType.bool, 2)
OR = Keyword("or", PositionType.infix, SchemaType.bool, 2)
NOT = Keyword("not", PositionType.prefix, SchemaType.bool, 1)


def builtin_keywords() -> LookupKeyword:
    funcs = [
        AND,
        OR,
        NOT,
    ]

    func_types = {_t: [] for _t in PositionType}
    for f in funcs:
        func_types[f.position_type].append(f.name)

    return LookupKeyword({f.name: f for f in funcs}, func_types)


@dataclasses.dataclass
class NodeType:
    type: Keyword | Symbol | Paren
    arguments: list[Keyword | Symbol | Literal | Name | Paren]
    parent: typing.Optional["NodeType"]


class Parser:
    def __init__(self, target, schema: Schema):
        self.original_target: str = target
        self.schema: Schema = schema
        self.pos: int = 0
        self.cur_pos_end: int | None = None
        self.tree = None
        self.cur_node = None
        self.token_stack = []

    def parse_all(self):
        while len(self.original_target[self.pos :]) > 0:
            token = self.next_token()
            match token:
                case Token(token_type=TokenType.string_literal):
                    self.parse_literal(token, SchemaType.str)
                case Token(token_type=TokenType.int_literal):
                    self.parse_literal(token, SchemaType.int)
                case Token(token_type=TokenType.symbol):
                    self.parse_symbol(token)
                case Token(token_type=TokenType.name):
                    self.parse_name(token)
                case Token(token_type=TokenType.whitespace):
                    pass

            self.next()

        return self.tree

    def peek(self, pos: int):
        return self.next_token(pos, move=False)

    def next_token(self, pos: int | None = None, move=True) -> Token:
        pos = pos if pos else self.pos

        target = self.original_target[pos:]
        for pattern, token_type in token_map.items():
            match_obj = pattern.match(target)
            if match_obj is None:
                continue
            value = match_obj.group(0)
            if move:
                self.cur_pos_end = match_obj.end()
            token = Token(value, token_type, match_obj.start(), match_obj.end())
            if token.token_type is TokenType.whitespace:
                self.next()
                return self.next_token()

            return token
        else:
            raise Exception(f"Unexpected characters at {self.original_target[pos:]}")

    def next(self, next_pos: int | None = None):

        if self.cur_pos_end is not None:

            # if it's None, we've already advanced it in some other case
            next_pos = next_pos if next_pos else max(self.cur_pos_end, self.pos)
            self.pos = next_pos + 1
            self.cur_pos_end = None

    def parse_literal(self, token: Token, schema_type: SchemaType):
        el = Literal(token.value, schema_type)
        if self.tree is None:
            self.token_stack.append(el)
        elif self.tree:
            self.cur_node.arguments.append(el)
        return el

    def parse_symbol(self, token: Token) -> NodeType:
        lookup_symbols = builtin_symbols()
        symbol: Symbol = lookup_symbols.token[token.value]
        if self.tree is None:
            node = NodeType(symbol, [self.token_stack.pop()], parent=None)
            self.cur_node = node
            self.tree = node
        elif self.tree:
            pass
        return node

    def parse_name(self, token: Token):
        match token.value:
            case name if return_type := self.schema.get_type(name):
                el = Name(name, return_type)

                if self.tree is None:
                    self.token_stack.append(el)
                elif self.tree:
                    self.cur_node.arguments.append(el)

            case name if keyword := builtin_keywords().get_type(name):
                if self.tree is None:
                    node = NodeType(keyword, [self.token_stack.pop()], parent=None)
                    self.cur_node = node
                    self.tree = node
                elif self.tree:
                    pass
            case _:
                raise Exception(f"Unknown name {token.value}")
        return

    def expect(self, token_types: list[TokenType]) -> Token | None:
        token: Token = self.peek(self.cur_pos_end + 1)
        if token.token_type in token_types:
            return token
        return None
