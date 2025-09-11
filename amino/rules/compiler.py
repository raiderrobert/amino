"""Rule compilation implementation."""

from collections.abc import Callable
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

    def __init__(self, rule_id: Any, evaluator: Callable[[dict[str, Any], dict[str, Callable]], bool],
                 variables: list[str], functions: list[str]):
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
        if isinstance(node, Literal):
            return lambda data, functions: node.value

        elif isinstance(node, Variable):
            def var_evaluator(data, functions):
                if node.name in data:
                    return data[node.name]
                # Handle dotted names (struct.field)
                if "." in node.name:
                    parts = node.name.split(".")
                    value = data
                    for part in parts:
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            raise RuleEvaluationError(f"Variable '{node.name}' not found in data")
                    return value
                raise RuleEvaluationError(f"Variable '{node.name}' not found in data")
            return var_evaluator

        elif isinstance(node, BinaryOp):
            left_eval = self._generate_evaluator(node.left)
            right_eval = self._generate_evaluator(node.right)

            def binary_evaluator(data, functions):
                left_val = left_eval(data, functions)

                # Short-circuit evaluation for logical operators
                if node.operator == Operator.AND:
                    if not left_val:
                        return False
                    return bool(right_eval(data, functions))
                elif node.operator == Operator.OR:
                    if left_val:
                        return True
                    return bool(right_eval(data, functions))

                # Evaluate right side for other operators
                right_val = right_eval(data, functions)

                if node.operator == Operator.EQ:
                    return left_val == right_val
                elif node.operator == Operator.NE:
                    return left_val != right_val
                elif node.operator == Operator.GT:
                    return left_val > right_val
                elif node.operator == Operator.LT:
                    return left_val < right_val
                elif node.operator == Operator.GTE:
                    return left_val >= right_val
                elif node.operator == Operator.LTE:
                    return left_val <= right_val
                elif node.operator == Operator.IN:
                    return left_val in right_val
                elif node.operator == Operator.NOT_IN:
                    return left_val not in right_val
                else:
                    raise RuleEvaluationError(f"Unknown binary operator: {node.operator}")

            return binary_evaluator

        elif isinstance(node, UnaryOp):
            operand_eval = self._generate_evaluator(node.operand)

            def unary_evaluator(data, functions):
                operand_val = operand_eval(data, functions)

                if node.operator == Operator.NOT:
                    return not bool(operand_val)
                else:
                    raise RuleEvaluationError(f"Unknown unary operator: {node.operator}")

            return unary_evaluator

        elif isinstance(node, FunctionCall):
            arg_evaluators = [self._generate_evaluator(arg) for arg in node.args]

            def function_evaluator(data, functions):
                if node.name not in functions:
                    raise RuleEvaluationError(f"Function '{node.name}' not found")

                func = functions[node.name]
                args = [evaluator(data, functions) for evaluator in arg_evaluators]
                return func(*args)

            return function_evaluator

        else:
            raise RuleEvaluationError(f"Unknown node type: {type(node)}")
