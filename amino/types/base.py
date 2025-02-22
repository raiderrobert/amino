"""
Core types and constants for the Amino type system.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import abc


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


class TypeError(Exception):
    """Raised when a type error occurs"""
    pass