"""ClickHouse compile target. Emits server-side typed ``{name:Type}`` parameters."""

from typing import Any

from amino.errors import UnsupportedExpressionError

from .base import ParamSink, SQLBackend

_SCALAR_TYPES: dict[str, str] = {
    "Int": "Int64",
    "Float": "Float64",
    "Str": "String",
    "Bool": "Bool",
}


def _ch_type(base_type: str) -> str:
    if base_type.startswith("List[") and base_type.endswith("]"):
        return f"Array({_ch_type(base_type[5:-1])})"
    try:
        return _SCALAR_TYPES[base_type]
    except KeyError:
        raise UnsupportedExpressionError(f"No ClickHouse type for '{base_type}'") from None


class _NamedParams(ParamSink):
    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def add(self, value: Any, base_type: str) -> str:
        name = f"p{len(self._values)}"
        self._values[name] = value
        return f"{{{name}:{_ch_type(base_type)}}}"

    def result(self) -> dict[str, Any]:
        return self._values


class ClickHouseBackend(SQLBackend):
    """Compile an expression to a ClickHouse ``WHERE`` predicate.

    ``Query.params`` is a dict for ``client.query(sql, parameters=params)``
    with clickhouse-connect. Placeholders carry the type inferred at parse
    time, so ClickHouse binds them server-side without string interpolation.
    """

    def quote_ident(self, name: str) -> str:
        return "`" + name.replace("\\", "\\\\").replace("`", "\\`") + "`"

    def new_params(self) -> ParamSink:
        return _NamedParams()

    def render_in(self, column: str, placeholder: str) -> str:
        return f"{column} IN {placeholder}"

    def render_not_in(self, column: str, placeholder: str) -> str:
        return f"{column} NOT IN {placeholder}"

    def render_contains(self, haystack: str, needle: str) -> str:
        return f"position({haystack}, {needle}) > 0"
