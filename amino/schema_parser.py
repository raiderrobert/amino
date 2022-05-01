import dataclasses
import enum
import regex

RESERVED_NAMES = ["and", "or", "not"]  # all casing variations of these are reserved

whitespace = regex.compile("[\\s]+")
word = regex.compile("[\\w]+")
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
            raise Exception(f"Unexpected characters at {target[pos:]}")
    return tokens


class SchemaType(enum.Enum):
    str = "str"
    int = "int"
    bool = "bool"
    any = "any"


def parse_types(_type):
    match _type:
        case "str":
            return SchemaType.str
        case "int":
            return SchemaType.int
        case "bool":
            return SchemaType.bool
        case "any":
            return SchemaType.any

    raise Exception(f"Unexpected type {_type}")


@dataclasses.dataclass
class Name:
    name: str
    name_type: SchemaType


class Schema:
    def __init__(self, names_list: list[Name]):
        self.name_list: list[Name] = names_list
        self.names_dict: dict[str, SchemaType] = {i.name: i.name_type for i in names_list}

    def get_type(self, name: str):
        return self.names_dict[name]


def parse_schema(schema) -> Schema:
    tokens = _tokenizer(schema)
    parsed_schema = []
    while len(tokens) > 0:
        match tokens:
            case [Token(name, TokenType.word), Token(_, TokenType.colon), Token(name_type, TokenType.word), *remainder]:
                parsed_schema.append(Name(name, parse_types(name_type)))
                tokens = remainder
            case _:
                raise Exception(f"Unexpected remainder {tokens}")
    return Schema(parsed_schema)


def load_schema(schema) -> Schema:
    schema: str = (
        schema
        or """
    foo: int
    """
    )

    return parse_schema(schema)
