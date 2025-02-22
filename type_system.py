from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Union, Callable, Optional, Set, Tuple
import abc

# ---- Type System ----

class TypeKind(Enum):
    INT = auto()
    STR = auto()
    FLOAT = auto()
    BOOL = auto()
    LIST = auto()
    STRUCT = auto()
    UNION = auto()
    FUNCTION = auto()

class Type(abc.ABC):
    """Base class for all types in the system"""
    kind: TypeKind
    
    def can_assign_from(self, other: 'Type') -> bool:
        """Check if this type can accept a value of another type"""
        return self == other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Type):
            return NotImplemented
        return self.kind == other.kind

@dataclass(frozen=True)
class PrimitiveType(Type):
    kind: TypeKind

    @classmethod
    def INT(cls) -> 'PrimitiveType':
        return cls(TypeKind.INT)
    
    @classmethod
    def STR(cls) -> 'PrimitiveType':
        return cls(TypeKind.STR)
    
    @classmethod
    def FLOAT(cls) -> 'PrimitiveType':
        return cls(TypeKind.FLOAT)
    
    @classmethod
    def BOOL(cls) -> 'PrimitiveType':
        return cls(TypeKind.BOOL)

@dataclass(frozen=True)
class ListType(Type):
    element_type: Type
    kind: TypeKind = TypeKind.LIST

    def can_assign_from(self, other: Type) -> bool:
        if not isinstance(other, ListType):
            return False
        return self.element_type.can_assign_from(other.element_type)

@dataclass(frozen=True)
class UnionType(Type):
    types: Set[Type]
    kind: TypeKind = TypeKind.UNION

    def can_assign_from(self, other: Type) -> bool:
        # A union can accept any of its member types
        if isinstance(other, UnionType):
            return all(any(t2.can_assign_from(t1) for t2 in self.types) 
                      for t1 in other.types)
        return any(t.can_assign_from(other) for t in self.types)

@dataclass(frozen=True)
class StructType(Type):
    name: str
    fields: Dict[str, Type]
    kind: TypeKind = TypeKind.STRUCT

    def can_assign_from(self, other: Type) -> bool:
        if not isinstance(other, StructType):
            return False
        if self.name != other.name:
            return False
        return all(
            self.fields[name].can_assign_from(other.fields[name])
            for name in self.fields
            if name in other.fields
        )

@dataclass(frozen=True)
class FunctionType(Type):
    arg_types: List[Type]
    return_type: Type
    default_args: Optional[Dict[str, Type]] = None
    kind: TypeKind = TypeKind.FUNCTION

    def can_assign_from(self, other: Type) -> bool:
        if not isinstance(other, FunctionType):
            return False
        if len(self.arg_types) != len(other.arg_types):
            return False
        return (all(t1.can_assign_from(t2) for t1, t2 in zip(self.arg_types, other.arg_types)) and
                self.return_type.can_assign_from(other.return_type))

# ---- Type Checker ----

class TypeError(Exception):
    pass

@dataclass
class TypeChecker:
    """Type checker for Amino expressions"""
    schema_types: Dict[str, Type]
    
    def check_expression(self, expr: 'Expression') -> Type:
        """Type check an expression and return its type"""
        return expr.accept(self)

    def check_binary_op(self, left: Type, op: str, right: Type) -> Type:
        """Type check a binary operation"""
        # Comparison operators
        if op in {'=', '!=', '>', '<', '>=', '<='}:
            if not (isinstance(left, PrimitiveType) and isinstance(right, PrimitiveType)):
                raise TypeError(f"Cannot compare non-primitive types: {left} {op} {right}")
            if left.kind != right.kind:
                raise TypeError(f"Type mismatch in comparison: {left} {op} {right}")
            return PrimitiveType.BOOL()
        
        # List membership
        if op in {'in', 'not in'}:
            if not isinstance(right, ListType):
                raise TypeError(f"Right operand of '{op}' must be a list, got {right}")
            if not right.element_type.can_assign_from(left):
                raise TypeError(f"Type mismatch in '{op}': {left} not compatible with list of {right.element_type}")
            return PrimitiveType.BOOL()
        
        # Logical operators
        if op in {'and', 'or'}:
            if not (isinstance(left, PrimitiveType) and left.kind == TypeKind.BOOL and
                   isinstance(right, PrimitiveType) and right.kind == TypeKind.BOOL):
                raise TypeError(f"Logical operator '{op}' requires boolean operands")
            return PrimitiveType.BOOL()
        
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

# ---- AST Nodes ----

class Expression(abc.ABC):
    """Base class for all expressions in the AST"""
    @abc.abstractmethod
    def accept(self, checker: TypeChecker) -> Type:
        """Accept a type checker visitor"""
        pass

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
    value: Union[int, str, float, bool]
    
    def accept(self, checker: TypeChecker) -> Type:
        if isinstance(self.value, int):
            return PrimitiveType.INT()
        elif isinstance(self.value, str):
            return PrimitiveType.STR()
        elif isinstance(self.value, float):
            return PrimitiveType.FLOAT()
        elif isinstance(self.value, bool):
            return PrimitiveType.BOOL()
        raise TypeError(f"Unknown literal type: {type(self.value)}")

# ---- Example Usage ----

def example_type_checking():
    # Define schema types
    schema_types = {
        "amount": PrimitiveType.INT(),
        "state_code": PrimitiveType.STR(),
        "smallest_number": FunctionType(
            arg_types=[PrimitiveType.INT(), PrimitiveType.INT()],
            return_type=PrimitiveType.INT()
        )
    }
    
    # Create type checker
    checker = TypeChecker(schema_types)
    
    # Example expression: amount > 0 and state_code = 'CA'
    expr = BinaryOp(
        left=BinaryOp(
            left=Identifier("amount"),
            op=">",
            right=Literal(0)
        ),
        op="and",
        right=BinaryOp(
            left=Identifier("state_code"),
            op="=",
            right=Literal("CA")
        )
    )
    
    # Type check the expression
    result_type = checker.check_expression(expr)
    assert result_type == PrimitiveType.BOOL()
    
    # This would raise a TypeError:
    # expr = BinaryOp(Identifier("amount"), "=", Identifier("state_code"))
    # checker.check_expression(expr)  # TypeError: Type mismatch