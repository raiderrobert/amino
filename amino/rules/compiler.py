# amino/rules/compiler.py
from collections.abc import Callable
from typing import Any

from amino.errors import RuleEvaluationError

from .ast import BinaryOp, FunctionCall, Literal, RuleAST, RuleNode, UnaryOp, Variable


class CompiledRule:
    def __init__(self, rule_id: Any, fn: Callable, return_type: str):
        self.rule_id = rule_id
        self._fn = fn
        self.return_type = return_type

    def evaluate(self, data: dict[str, Any],
                 functions: dict[str, Callable]) -> Any:
        try:
            return self._fn(data, functions)
        except RuleEvaluationError:
            return False
        except Exception:
            return False


class TypedCompiler:
    def __init__(self, rules_mode: str = "strict"):
        self.rules_mode = rules_mode

    def compile(self, rule_id: Any, ast: RuleAST) -> CompiledRule:
        fn = self._build(ast.root)
        return CompiledRule(rule_id, fn, ast.return_type)

    def _build(self, node: RuleNode) -> Callable:
        if isinstance(node, Literal):
            v = node.value
            return lambda data, fns, _v=v: _v

        if isinstance(node, Variable):
            name = node.name
            if "." in name:
                parts = name.split(".")
                def var_fn(data, fns, _parts=parts):
                    cur = data
                    for p in _parts:
                        if isinstance(cur, dict) and p in cur:
                            cur = cur[p]
                        else:
                            raise RuleEvaluationError(f"Field '{name}' not found")
                    return cur
                return var_fn
            else:
                def simple_var(data, fns, _n=name):
                    if _n not in data:
                        raise RuleEvaluationError(f"Field '{_n}' not found")
                    return data[_n]
                return simple_var

        if isinstance(node, UnaryOp):
            operand_fn = self._build(node.operand)
            op_fn = node.fn
            def unary(data, fns, _op=operand_fn, _fn=op_fn):
                return _fn(_op(data, fns))
            return unary

        if isinstance(node, BinaryOp):
            left_fn = self._build(node.left)
            right_fn = self._build(node.right)
            op = node.op_token
            op_fn = node.fn
            if op == "and":
                def and_fn(data, fns, _left=left_fn, _right=right_fn):
                    try:
                        lv = bool(_left(data, fns))
                    except RuleEvaluationError:
                        return False
                    return lv and bool(_right(data, fns))
                return and_fn
            if op == "or":
                def or_fn(data, fns, _left=left_fn, _right=right_fn):
                    try:
                        lv = bool(_left(data, fns))
                    except RuleEvaluationError:
                        lv = False
                    if lv:
                        return True
                    try:
                        return bool(_right(data, fns))
                    except RuleEvaluationError:
                        return False
                return or_fn
            def binary(data, fns, _left=left_fn, _right=right_fn, _fn=op_fn):
                return _fn(_left(data, fns), _right(data, fns))
            return binary

        if isinstance(node, FunctionCall):
            arg_fns = [self._build(a) for a in node.args]
            name = node.name
            def call_fn(data, fns, _name=name, _args=arg_fns):
                if _name not in fns:
                    raise RuleEvaluationError(f"Function '{_name}' not found")
                return fns[_name](*[f(data, fns) for f in _args])
            return call_fn

        raise RuleEvaluationError(f"Unknown node type: {type(node)}")
