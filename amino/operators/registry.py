import dataclasses
from collections.abc import Callable

from amino.errors import OperatorConflictError


@dataclasses.dataclass
class OperatorDef:
    fn: Callable | None
    binding_power: int
    symbol: str | None = None
    keyword: str | None = None
    kind: str = "infix"
    associativity: str = "left"
    input_types: tuple[str, ...] = ("*", "*")
    return_type: str = "Bool"

    def __post_init__(self):
        if not self.symbol and not self.keyword:
            raise ValueError("OperatorDef requires symbol or keyword")

    @property
    def token(self) -> str:
        return self.symbol or self.keyword  # type: ignore[return-value]


class OperatorRegistry:
    def __init__(self):
        self._by_token: dict[str, list[OperatorDef]] = {}
        self._symbols: set[str] = set()
        self._keywords: set[str] = set()

    def register(self, op: OperatorDef) -> None:
        token = op.token
        for existing in self._by_token.get(token, []):
            if existing.input_types == op.input_types:
                raise OperatorConflictError(
                    f"Operator '{token}' with input_types {op.input_types} already registered"
                )
        self._by_token.setdefault(token, []).append(op)
        if op.symbol:
            self._symbols.add(op.symbol)
        else:
            self._keywords.add(op.keyword)  # type: ignore[arg-type]

    def lookup_by_types(self, token: str, input_types: tuple[str, ...]) -> OperatorDef | None:
        candidates = self._by_token.get(token, [])
        # Exact match first
        for op in candidates:
            if op.input_types == input_types:
                return op
        # Wildcard fallback
        for op in candidates:
            if len(op.input_types) == len(input_types):
                if all(e == "*" or e == a for e, a in zip(op.input_types, input_types, strict=False)):
                    return op
        return candidates[0] if len(candidates) == 1 else None

    def lookup_symbol(self, symbol: str) -> OperatorDef | None:
        if symbol not in self._symbols:
            return None
        c = self._by_token.get(symbol, [])
        return c[0] if c else None

    def lookup_keyword(self, keyword: str) -> OperatorDef | None:
        if keyword not in self._keywords:
            return None
        c = self._by_token.get(keyword, [])
        return c[0] if c else None

    def get_binding_power(self, token: str) -> int | None:
        c = self._by_token.get(token, [])
        return c[0].binding_power if c else None

    def is_symbol(self, token: str) -> bool:
        return token in self._symbols

    def is_keyword(self, token: str) -> bool:
        return token in self._keywords

    def all_symbols(self) -> set[str]:
        return set(self._symbols)

    def all_keywords(self) -> set[str]:
        return set(self._keywords)
