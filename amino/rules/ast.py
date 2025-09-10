"""Rule AST definitions."""

import dataclasses
import enum
from typing import List, Any, Union, Optional
from ..schema.types import SchemaType


class Operator(enum.Enum):
    """Rule operators."""
    # Comparison
    EQ = "="
    NE = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    
    # Logical
    AND = "and"
    OR = "or"
    NOT = "not"
    
    # Membership
    IN = "in"
    NOT_IN = "not in"
    
    # Type checking
    TYPEOF = "typeof"
    IS_VALID = "is_valid"


@dataclasses.dataclass
class RuleNode:
    """Base class for rule AST nodes."""
    return_type: SchemaType


@dataclasses.dataclass
class Literal(RuleNode):
    """Literal value in a rule."""
    value: Any
    
    def __init__(self, value: Any, return_type: SchemaType):
        self.value = value
        self.return_type = return_type
    

@dataclasses.dataclass
class Variable(RuleNode):
    """Variable reference in a rule."""
    name: str
    
    def __init__(self, name: str, return_type: SchemaType):
        self.name = name
        self.return_type = return_type
    

@dataclasses.dataclass
class BinaryOp(RuleNode):
    """Binary operation in a rule."""
    operator: Operator
    left: RuleNode
    right: RuleNode
    
    def __init__(self, operator: Operator, left: RuleNode, right: RuleNode, return_type: SchemaType):
        self.operator = operator
        self.left = left
        self.right = right
        self.return_type = return_type


@dataclasses.dataclass
class UnaryOp(RuleNode):
    """Unary operation in a rule."""
    operator: Operator
    operand: RuleNode
    
    def __init__(self, operator: Operator, operand: RuleNode, return_type: SchemaType):
        self.operator = operator
        self.operand = operand
        self.return_type = return_type


@dataclasses.dataclass
class FunctionCall(RuleNode):
    """Function call in a rule."""
    name: str
    args: List[RuleNode]
    
    def __init__(self, name: str, args: List[RuleNode], return_type: SchemaType):
        self.name = name
        self.args = args
        self.return_type = return_type


@dataclasses.dataclass
class RuleAST:
    """Rule abstract syntax tree."""
    root: RuleNode
    variables: List[str] = dataclasses.field(default_factory=list)
    functions: List[str] = dataclasses.field(default_factory=list)