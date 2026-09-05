"""Postgres compile target. Emits psycopg-style positional ``%s`` parameters."""

from typing import Any

from .base import ParamSink, SQLBackend


class _PositionalParams(ParamSink):
    def __init__(self) -> None:
        self._values: list[Any] = []

    def add(self, value: Any, base_type: str) -> str:
        self._values.append(value)
        return "%s"

    def result(self) -> list[Any]:
        return self._values


class PostgresBackend(SQLBackend):
    """Compile an expression to a Postgres ``WHERE`` predicate.

    ``Query.params`` is a list suitable for ``cursor.execute(sql, params)``
    with psycopg. List membership renders as ``col = ANY(%s)`` so a Python
    list binds as a single array parameter.
    """

    def quote_ident(self, name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    def new_params(self) -> ParamSink:
        return _PositionalParams()

    def render_in(self, column: str, placeholder: str) -> str:
        return f"{column} = ANY({placeholder})"

    def render_contains(self, haystack: str, needle: str) -> str:
        return f"position({needle} IN {haystack}) > 0"
