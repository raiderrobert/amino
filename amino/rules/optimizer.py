"""Rule optimization implementation."""

from ..schema.types import SchemaType
from .ast import BinaryOp, Literal, Operator, RuleAST, RuleNode, UnaryOp


class RuleOptimizer:
    """Optimizes rule ASTs for better performance."""

    def optimize(self, ast: RuleAST) -> RuleAST:
        """Apply optimizations to rule AST."""
        optimized_root = self._optimize_node(ast.root)
        return RuleAST(optimized_root, ast.variables, ast.functions)

    def _optimize_node(self, node: RuleNode) -> RuleNode:
        """Recursively optimize a node."""
        if isinstance(node, BinaryOp):
            return self._optimize_binary_op(node)
        elif isinstance(node, UnaryOp):
            return self._optimize_unary_op(node)
        else:
            return node

    def _optimize_binary_op(self, node: BinaryOp) -> RuleNode:
        """Optimize binary operations."""
        # Recursively optimize children first
        left = self._optimize_node(node.left)
        right = self._optimize_node(node.right)

        # Constant folding
        if isinstance(left, Literal) and isinstance(right, Literal):
            return self._evaluate_literal_binary_op(node.operator, left, right, node)

        # Boolean optimizations
        if node.operator == Operator.AND:
            # true AND x = x
            if isinstance(left, Literal) and left.value is True:
                return right
            # false AND x = false
            if isinstance(left, Literal) and left.value is False:
                return Literal(False, SchemaType.bool)
            # x AND true = x
            if isinstance(right, Literal) and right.value is True:
                return left
            # x AND false = false
            if isinstance(right, Literal) and right.value is False:
                return Literal(False, SchemaType.bool)

        elif node.operator == Operator.OR:
            # true OR x = true
            if isinstance(left, Literal) and left.value is True:
                return Literal(True, SchemaType.bool)
            # false OR x = x
            if isinstance(left, Literal) and left.value is False:
                return right
            # x OR true = true
            if isinstance(right, Literal) and right.value is True:
                return Literal(True, SchemaType.bool)
            # x OR false = x
            if isinstance(right, Literal) and right.value is False:
                return left

        return BinaryOp(node.operator, left, right, node.return_type)

    def _optimize_unary_op(self, node: UnaryOp) -> RuleNode:
        """Optimize unary operations."""
        operand = self._optimize_node(node.operand)

        # Constant folding for NOT
        if node.operator == Operator.NOT and isinstance(operand, Literal):
            if isinstance(operand.value, bool):
                return Literal(not operand.value, SchemaType.bool)

        # Double negation elimination: NOT NOT x = x
        if node.operator == Operator.NOT and isinstance(operand, UnaryOp) and operand.operator == Operator.NOT:
            return operand.operand

        return UnaryOp(node.operator, operand, node.return_type)

    def _evaluate_literal_binary_op(
        self, operator: Operator, left: Literal, right: Literal, original_node: BinaryOp
    ) -> RuleNode:
        """Evaluate binary operation on two literals."""
        if operator == Operator.EQ:
            return Literal(left.value == right.value, SchemaType.bool)
        elif operator == Operator.NE:
            return Literal(left.value != right.value, SchemaType.bool)
        elif operator == Operator.GT:
            return Literal(left.value > right.value, SchemaType.bool)
        elif operator == Operator.LT:
            return Literal(left.value < right.value, SchemaType.bool)
        elif operator == Operator.GTE:
            return Literal(left.value >= right.value, SchemaType.bool)
        elif operator == Operator.LTE:
            return Literal(left.value <= right.value, SchemaType.bool)
        elif operator == Operator.AND:
            return Literal(bool(left.value) and bool(right.value), SchemaType.bool)
        elif operator == Operator.OR:
            return Literal(bool(left.value) or bool(right.value), SchemaType.bool)
        elif operator == Operator.IN:
            return Literal(left.value in right.value, SchemaType.bool)
        elif operator == Operator.NOT_IN:
            return Literal(left.value not in right.value, SchemaType.bool)

        return original_node
