import dataclasses
import enum
import regex


RESERVED_NAMES = ['and', 'or', 'not']  # all casing variations of these are reserved


whitespace = regex.compile("[\s]+")
word = regex.compile("[\w]+")
colon = regex.compile(":")


class TokenType(enum.Enum):
    whitespace = 1
    word = 2
    colon = 3


token_map = {
    whitespace: TokenType.whitespace,
    word: TokenType.word,
    colon: TokenType.colon,
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
                    if str(value).lower() in RESERVED_NAMES:
                        raise Exception(f"Cannot declare reserved name: {RESERVED_NAMES}")
                    tokens.append(Token(value, token_type))
                pos = match_obj.end()
                target = target[pos:]
                break
        else:
            raise Exception(f'Unexpected characters at {target[pos:]}')
    return tokens


class SchemaType(enum.Enum):
    str = 'str'
    int = 'int'
    bool = 'bool'
    any = 'any'


def parse_types(_type):
    match _type:
        case "str":
            return SchemaType.str
        case "int":
            return SchemaType.int

    raise Exception(f'Unexpected type {_type}')


@dataclasses.dataclass
class Names:
    name: str
    _type: SchemaType


def parse_schema(schema) -> list[Names]:
    tokens = _tokenizer(schema)
    parsed_schema = []
    while len(tokens) > 0:
        match tokens:
            case [Token(name, TokenType.word), Token(_, TokenType.colon), Token(_type, TokenType.word), *remainder]:
                parsed_schema.append(
                    Names(name, parse_types(_type))
                )
                tokens = remainder
            case _:
                raise Exception(f'Unexpected remainder {tokens}')

    return parsed_schema


def load_schema():
    schema: str = """
    foo: int
    """

    return parse_schema(schema)