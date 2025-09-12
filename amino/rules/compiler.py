"""Rule compilation implementation."""

from collections.abc import Callable
from functools import lru_cache, singledispatch
from typing import Any

from ..utils.errors import RuleEvaluationError
from .ast import (
    BinaryOp,
    FunctionCall,
    Literal,
    Operator,
    RuleAST,
    RuleNode,
    UnaryOp,
    Variable,
)


class CompiledRule:
    """Compiled rule that can be evaluated efficiently."""

    def __init__(
        self,
        rule_id: Any,
        evaluator: Callable[[dict[str, Any], dict[str, Callable]], bool],
        variables: list[str],
        functions: list[str],
    ):
        self.rule_id = rule_id
        self.evaluator = evaluator
        self.variables = variables
        self.functions = functions

    def evaluate(self, data: dict[str, Any], function_registry: dict[str, Callable] | None = None) -> bool:
        """Evaluate the compiled rule against data."""
        try:
            return self.evaluator(data, function_registry or {})
        except Exception as e:
            raise RuleEvaluationError(f"Error evaluating rule {self.rule_id}: {e}") from e


class RuleCompiler:
    """Compiles rule ASTs into executable code."""

    def compile_rule(self, rule_id: Any, ast: RuleAST) -> CompiledRule:
        """Compile a single rule AST."""
        evaluator_code = self._generate_evaluator(ast.root)

        def evaluator(data: dict[str, Any], functions: dict[str, Callable] | None = None) -> bool:
            functions = functions or {}
            return evaluator_code(data, functions)

        return CompiledRule(rule_id, evaluator, ast.variables, ast.functions)

    def compile_rules(self, rules: list[tuple[Any, RuleAST]]) -> list[CompiledRule]:
        """Compile multiple rules."""
        return [self.compile_rule(rule_id, ast) for rule_id, ast in rules]

    def _generate_evaluator(self, node: RuleNode) -> Callable:
        """Generate evaluator function for a node."""
        return generate_evaluator(node)


# Functional evaluator generation using single dispatch
@singledispatch
def generate_evaluator(node: RuleNode) -> Callable:
    """Generate evaluator function for a node using single dispatch."""
    raise RuleEvaluationError(f"Unknown node type: {type(node)}")


@generate_evaluator.register
def _(node: Literal) -> Callable:
    """Generate evaluator for literal values."""
    value = node.value
    return lambda data, functions: value


@generate_evaluator.register
def _(node: Variable) -> Callable:
    """Generate evaluator for variable access."""
    name = node.name

    def var_evaluator(data, functions):
        if name in data:
            return data[name]
        # Handle dotted names (struct.field)
        if "." in name:
            return evaluate_dotted_variable(name, data)
        raise RuleEvaluationError(f"Variable '{name}' not found in data")

    return var_evaluator


@lru_cache(maxsize=256)
def get_dotted_parts(name: str) -> tuple[str, ...]:
    """Cache the parsing of dotted variable names."""
    return tuple(name.split("."))


def evaluate_dotted_variable(name: str, data: dict) -> Any:
    """Evaluate dotted variable names like 'struct.field'."""
    parts = get_dotted_parts(name)
    value = data
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise RuleEvaluationError(f"Variable '{name}' not found in data")
    return value


@generate_evaluator.register
def _(node: BinaryOp) -> Callable:
    """Generate evaluator for binary operations."""
    left_eval = generate_evaluator(node.left)
    right_eval = generate_evaluator(node.right)
    operator = node.operator

    def binary_evaluator(data, functions):
        left_val = left_eval(data, functions)

        # Short-circuit evaluation for logical operators
        if operator == Operator.AND:
            return left_val and bool(right_eval(data, functions))
        elif operator == Operator.OR:
            return left_val or bool(right_eval(data, functions))

        # Evaluate right side for comparison operators
        right_val = right_eval(data, functions)
        operation = get_binary_operation(operator)
        return operation(left_val, right_val)

    return binary_evaluator


@lru_cache(maxsize=128)
def get_binary_operation(operator: Operator) -> Callable[[Any, Any], bool]:
    """Cache binary operation functions by operator type."""
    match operator:
        case Operator.EQ:
            return lambda l, r: l == r
        case Operator.NE:
            return lambda l, r: l != r
        case Operator.GT:
            return lambda l, r: l > r
        case Operator.LT:
            return lambda l, r: l < r
        case Operator.GTE:
            return lambda l, r: l >= r
        case Operator.LTE:
            return lambda l, r: l <= r
        case Operator.IN:
            return lambda l, r: l in r
        case Operator.NOT_IN:
            return lambda l, r: l not in r
        case _:
            raise RuleEvaluationError(f"Unknown binary operator: {operator}")


def evaluate_binary_operation(operator: Operator, left_val: Any, right_val: Any) -> bool:
    """Evaluate binary operation using cached operation functions."""
    operation = get_binary_operation(operator)
    return operation(left_val, right_val)


@generate_evaluator.register
def _(node: UnaryOp) -> Callable:
    """Generate evaluator for unary operations."""
    operand_eval = generate_evaluator(node.operand)
    operator = node.operator

    def unary_evaluator(data, functions):
        operand_val = operand_eval(data, functions)
        if operator == Operator.NOT:
            return not bool(operand_val)
        else:
            raise RuleEvaluationError(f"Unknown unary operator: {operator}")

    return unary_evaluator


@generate_evaluator.register
def _(node: FunctionCall) -> Callable:
    """Generate evaluator for function calls."""
    arg_evaluators = [generate_evaluator(arg) for arg in node.args]
    func_name = node.name

    def function_evaluator(data, functions):
        if func_name not in functions:
            raise RuleEvaluationError(f"Function '{func_name}' not found")

        func = functions[func_name]
        args = [evaluator(data, functions) for evaluator in arg_evaluators]
        return func(*args)

    return function_evaluator
