# amino/rules/ast.py
import dataclasses
from collections.abc import Callable
from typing import Any


@dataclasses.dataclass
class RuleNode:
    type_name: str   # resolved type: "Bool", "Int", "ipv4", etc.


@dataclasses.dataclass
class Literal(RuleNode):
    value: Any

    def __init__(self, value: Any, type_name: str):
        self.value = value
        self.type_name = type_name


@dataclasses.dataclass
class Variable(RuleNode):
    name: str

    def __init__(self, name: str, type_name: str):
        self.name = name
        self.type_name = type_name


@dataclasses.dataclass
class BinaryOp(RuleNode):
    op_token: str
    left: RuleNode
    right: RuleNode
    fn: Callable

    def __init__(self, op_token: str, left: RuleNode, right: RuleNode,
                 type_name: str, fn: Callable):
        self.op_token = op_token
        self.left = left
        self.right = right
        self.type_name = type_name
        self.fn = fn


@dataclasses.dataclass
class UnaryOp(RuleNode):
    op_token: str
    operand: RuleNode
    fn: Callable

    def __init__(self, op_token: str, operand: RuleNode, type_name: str, fn: Callable):
        self.op_token = op_token
        self.operand = operand
        self.type_name = type_name
        self.fn = fn


@dataclasses.dataclass
class FunctionCall(RuleNode):
    name: str
    args: list[RuleNode]

    def __init__(self, name: str, args: list[RuleNode], type_name: str):
        self.name = name
        self.args = args
        self.type_name = type_name


@dataclasses.dataclass
class RuleAST:
    root: RuleNode
    return_type: str
