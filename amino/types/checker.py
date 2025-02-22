"""
Type checker for Amino expressions.
"""

from dataclasses import dataclass
from typing import Dict, List

from amino.types.base import Type, TypeError, PrimitiveType, TypeKind, ListType, FunctionType


@dataclass
class TypeChecker:
    """Type checker for Amino expressions"""
    schema_types: Dict[str, Type]
    
    def check_expression(self, expr: 'Expression') -> Type:
        """Type check an expression and return its type"""
        from amino.types.expressions import Expression
        return expr.accept(self)

    def check_binary_op(self, left: Type, op: str, right: Type) -> Type:
        """Type check a binary operation"""
        # Comparison operators
        if op in {'=', '!=', '>', '<', '>=', '<='}:
            if not (isinstance(left, PrimitiveType) and isinstance(right, PrimitiveType)):
                raise TypeError(f"Cannot compare non-primitive types: {left} {op} {right}")
            if left.kind != right.kind:
                raise TypeError(f"Type mismatch in comparison: {left} {op} {right}")
            return PrimitiveType(TypeKind.BOOL)
        
        # List membership
        if op in {'in', 'not in'}:
            if not isinstance(right, ListType):
                raise TypeError(f"Right operand of '{op}' must be a list, got {right}")
            if not right.element_type.can_assign_from(left):
                raise TypeError(f"Type mismatch in '{op}': {left} not compatible with list of {right.element_type}")
            return PrimitiveType(TypeKind.BOOL)
        
        # Logical operators
        if op in {'and', 'or'}:
            if not (isinstance(left, PrimitiveType) and left.kind == TypeKind.BOOL and
                   isinstance(right, PrimitiveType) and right.kind == TypeKind.BOOL):
                raise TypeError(f"Logical operator '{op}' requires boolean operands")
            return PrimitiveType(TypeKind.BOOL)
        
        raise TypeError(f"Unknown operator: {op}")

    def check_function_call(self, func_type: FunctionType, args: List[Type]) -> Type:
        """Type check a function call"""
        if len(args) != len(func_type.arg_types):
            raise TypeError(
                f"Function call with wrong number of arguments. Expected {len(func_type.arg_types)}, got {len(args)}")
        
        for i, (expected, actual) in enumerate(zip(func_type.arg_types, args)):
            if not expected.can_assign_from(actual):
                raise TypeError(
                    f"Type mismatch in argument {i}: expected {expected}, got {actual}")
        
        return func_type.return_type