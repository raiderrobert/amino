"""
AST nodes and expressions.
"""

from dataclasses import dataclass
from typing import Any, List

from amino.types.base import Type, TypeError, FunctionType
from amino.types.base import PrimitiveType, TypeKind
from amino.types.checker import TypeChecker


class Expression:
    """Base class for all expressions in the AST"""
    def accept(self, checker: TypeChecker) -> Type:
        """Accept a type checker visitor"""
        raise NotImplementedError


@dataclass
class BinaryOp(Expression):
    left: Expression
    op: str
    right: Expression
    
    def accept(self, checker: TypeChecker) -> Type:
        left_type = self.left.accept(checker)
        right_type = self.right.accept(checker)
        return checker.check_binary_op(left_type, self.op, right_type)


@dataclass
class Identifier(Expression):
    name: str
    
    def accept(self, checker: TypeChecker) -> Type:
        if self.name not in checker.schema_types:
            raise TypeError(f"Unknown identifier: {self.name}")
        return checker.schema_types[self.name]


@dataclass
class FunctionCall(Expression):
    name: str
    args: List[Expression]
    
    def accept(self, checker: TypeChecker) -> Type:
        if self.name not in checker.schema_types:
            raise TypeError(f"Unknown function: {self.name}")
        
        func_type = checker.schema_types[self.name]
        if not isinstance(func_type, FunctionType):
            raise TypeError(f"{self.name} is not a function")
        
        arg_types = [arg.accept(checker) for arg in self.args]
        return checker.check_function_call(func_type, arg_types)


@dataclass
class Literal(Expression):
    value: Any
    
    def accept(self, checker: TypeChecker) -> Type:
        if isinstance(self.value, int):
            return PrimitiveType(TypeKind.INT)
        elif isinstance(self.value, str):
            return PrimitiveType(TypeKind.STR)
        elif isinstance(self.value, float):
            return PrimitiveType(TypeKind.FLOAT)
        elif isinstance(self.value, bool):
            return PrimitiveType(TypeKind.BOOL)
        raise TypeError(f"Unknown literal type: {type(self.value)}")