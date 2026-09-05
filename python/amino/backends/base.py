"""Shared SQL compile target.

A backend walks a typed ``Expression`` and produces a parameterised SQL
predicate. Everything dialect-specific lives behind a handful of hooks so
each dialect is a few dozen lines.
"""

import abc
import dataclasses
from typing import Any

from amino.errors import UnsupportedExpressionError
from amino.expression import Expression
from amino.rules.ast import BinaryOp, FunctionCall, Literal, RuleNode, UnaryOp, Variable

_COMPARISONS: dict[str, str] = {
    "=": "=",
    "!=": "<>",
    ">": ">",
    "<": "<",
    ">=": ">=",
    "<=": "<=",
}


@dataclasses.dataclass(frozen=True)
class Query:
    """A SQL fragment and the parameters bound to it.

    ``params`` is a ``list`` for positional dialects and a ``dict`` for
    named ones. Literals are never inlined into ``sql``.
    """

    sql: str
    params: Any


class ParamSink(abc.ABC):
    """Collects bound parameters for one ``compile()`` call."""

    @abc.abstractmethod
    def add(self, value: Any, base_type: str) -> str:
        """Bind ``value`` and return the placeholder to splice into the SQL."""

    @abc.abstractmethod
    def result(self) -> Any:
        """Return the collected parameters in the dialect's shape."""


def _element_base_type(values: list[Any]) -> str:
    """Infer the base type of a homogeneous list literal from its first element."""
    if not values:
        return "Str"
    first = values[0]
    if isinstance(first, bool):
        return "Bool"
    if isinstance(first, int):
        return "Int"
    if isinstance(first, float):
        return "Float"
    if isinstance(first, str):
        return "Str"
    raise UnsupportedExpressionError(f"Cannot bind list element of type {type(first).__name__}")


class SQLBackend(abc.ABC):
    """Compile an ``Expression`` into a ``Query`` for one SQL dialect.

    ``columns`` maps a DSL field path to a SQL fragment rendered verbatim in
    its place. Use it for nested struct fields (``customer.tier``) and for
    tables whose column names differ from the schema. Mapped fragments are
    trusted SQL written by the integrator, not user input.
    """

    def __init__(self, *, columns: dict[str, str] | None = None):
        self._columns: dict[str, str] = dict(columns or {})

    # ── dialect hooks ─────────────────────────────────────────────────

    @abc.abstractmethod
    def quote_ident(self, name: str) -> str: ...

    @abc.abstractmethod
    def new_params(self) -> ParamSink: ...

    @abc.abstractmethod
    def render_in(self, column: str, placeholder: str) -> str: ...

    def render_not_in(self, column: str, placeholder: str) -> str:
        return f"NOT ({self.render_in(column, placeholder)})"

    @abc.abstractmethod
    def render_contains(self, haystack: str, needle: str) -> str: ...

    # ── public API ────────────────────────────────────────────────────

    def compile(self, expr: Expression) -> Query:
        sink = self.new_params()
        sql = self._render(expr.ast.root, expr, sink)
        return Query(sql=sql, params=sink.result())

    # ── tree walk ─────────────────────────────────────────────────────

    def _render(self, node: RuleNode, expr: Expression, sink: ParamSink) -> str:
        if isinstance(node, Literal):
            return self._render_literal(node, expr, sink)
        if isinstance(node, Variable):
            return self._render_variable(node)
        if isinstance(node, UnaryOp):
            return self._render_unary(node, expr, sink)
        if isinstance(node, BinaryOp):
            return self._render_binary(node, expr, sink)
        if isinstance(node, FunctionCall):
            args = ", ".join(self._render(a, expr, sink) for a in node.args)
            return f"{node.name}({args})"
        raise UnsupportedExpressionError(f"Unknown node type: {type(node).__name__}")

    def _render_literal(self, node: Literal, expr: Expression, sink: ParamSink) -> str:
        if node.type_name == "List":
            raise UnsupportedExpressionError("List literals are only supported on the right of 'in' / 'not in'")
        return sink.add(node.value, expr.base_type(node.type_name))

    def _render_variable(self, node: Variable) -> str:
        mapped = self._columns.get(node.name)
        if mapped is not None:
            return mapped
        if "." in node.name:
            raise UnsupportedExpressionError(
                f"Nested field '{node.name}' has no column mapping; pass columns={{'{node.name}': ...}}"
            )
        return self.quote_ident(node.name)

    def _render_unary(self, node: UnaryOp, expr: Expression, sink: ParamSink) -> str:
        if node.op_token != "not":
            raise UnsupportedExpressionError(f"Operator '{node.op_token}' is not supported by {type(self).__name__}")
        return f"(NOT {self._render(node.operand, expr, sink)})"

    def _render_binary(self, node: BinaryOp, expr: Expression, sink: ParamSink) -> str:
        op = node.op_token
        if op in ("and", "or"):
            left = self._render(node.left, expr, sink)
            right = self._render(node.right, expr, sink)
            return f"({left} {op.upper()} {right})"
        if op in _COMPARISONS:
            left = self._render(node.left, expr, sink)
            right = self._render(node.right, expr, sink)
            return f"({left} {_COMPARISONS[op]} {right})"
        if op in ("in", "not in"):
            return self._render_membership(node, expr, sink)
        if op == "contains":
            haystack = self._render(node.left, expr, sink)
            needle = self._render(node.right, expr, sink)
            return f"({self.render_contains(haystack, needle)})"
        raise UnsupportedExpressionError(f"Operator '{op}' is not supported by {type(self).__name__}")

    def _render_membership(self, node: BinaryOp, expr: Expression, sink: ParamSink) -> str:
        right = node.right
        if not isinstance(right, Literal) or right.type_name != "List":
            raise UnsupportedExpressionError("'in' / 'not in' require a list literal on the right")
        values: list[Any] = list(right.value)
        negated = node.op_token == "not in"
        if not values:
            return "TRUE" if negated else "FALSE"
        left = self._render(node.left, expr, sink)
        placeholder = sink.add(values, f"List[{_element_base_type(values)}]")
        rendered = self.render_not_in(left, placeholder) if negated else self.render_in(left, placeholder)
        return f"({rendered})"
