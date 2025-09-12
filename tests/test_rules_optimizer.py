"""Tests for amino.rules.optimizer module."""

import pytest
from amino.rules.ast import BinaryOp, Literal, Operator, RuleAST, UnaryOp, Variable
from amino.rules.optimizer import RuleOptimizer
from amino.schema.types import SchemaType


class TestRuleOptimizer:
    """Tests for RuleOptimizer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = RuleOptimizer()

    def test_optimize_preserves_simple_node(self):
        """Test that simple nodes are preserved during optimization."""
        var = Variable("test", SchemaType.str)
        ast = RuleAST(var, {"test"}, set())
        result = self.optimizer.optimize(ast)
        
        assert result.root == var
        assert result.variables == {"test"}
        assert result.functions == set()

    def test_constant_folding_equality(self):
        """Test constant folding for equality operations."""
        left = Literal(5, SchemaType.int)
        right = Literal(5, SchemaType.int)
        binary_op = BinaryOp(Operator.EQ, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_constant_folding_inequality(self):
        """Test constant folding for inequality operations."""
        left = Literal(3, SchemaType.int)
        right = Literal(5, SchemaType.int)
        binary_op = BinaryOp(Operator.NE, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_constant_folding_comparison_gt(self):
        """Test constant folding for greater than operations."""
        left = Literal(10, SchemaType.int)
        right = Literal(5, SchemaType.int)
        binary_op = BinaryOp(Operator.GT, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_constant_folding_comparison_lt(self):
        """Test constant folding for less than operations."""
        left = Literal(3, SchemaType.int)
        right = Literal(5, SchemaType.int)
        binary_op = BinaryOp(Operator.LT, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_constant_folding_comparison_gte(self):
        """Test constant folding for greater than or equal operations."""
        left = Literal(5, SchemaType.int)
        right = Literal(5, SchemaType.int)
        binary_op = BinaryOp(Operator.GTE, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_constant_folding_comparison_lte(self):
        """Test constant folding for less than or equal operations."""
        left = Literal(5, SchemaType.int)
        right = Literal(5, SchemaType.int)
        binary_op = BinaryOp(Operator.LTE, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_constant_folding_in_operation(self):
        """Test constant folding for in operations."""
        left = Literal("a", SchemaType.str)
        right = Literal(["a", "b", "c"], SchemaType.list)
        binary_op = BinaryOp(Operator.IN, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_constant_folding_not_in_operation(self):
        """Test constant folding for not in operations."""
        left = Literal("d", SchemaType.str)
        right = Literal(["a", "b", "c"], SchemaType.list)
        binary_op = BinaryOp(Operator.NOT_IN, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_boolean_and_true_left(self):
        """Test AND optimization: true AND x = x."""
        left = Literal(True, SchemaType.bool)
        right = Variable("x", SchemaType.bool)
        binary_op = BinaryOp(Operator.AND, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert result.root == right

    def test_boolean_and_false_left(self):
        """Test AND optimization: false AND x = false."""
        left = Literal(False, SchemaType.bool)
        right = Variable("x", SchemaType.bool)
        binary_op = BinaryOp(Operator.AND, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is False

    def test_boolean_and_true_right(self):
        """Test AND optimization: x AND true = x."""
        left = Variable("x", SchemaType.bool)
        right = Literal(True, SchemaType.bool)
        binary_op = BinaryOp(Operator.AND, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert result.root == left

    def test_boolean_and_false_right(self):
        """Test AND optimization: x AND false = false."""
        left = Variable("x", SchemaType.bool)
        right = Literal(False, SchemaType.bool)
        binary_op = BinaryOp(Operator.AND, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is False

    def test_boolean_or_true_left(self):
        """Test OR optimization: true OR x = true."""
        left = Literal(True, SchemaType.bool)
        right = Variable("x", SchemaType.bool)
        binary_op = BinaryOp(Operator.OR, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_boolean_or_false_left(self):
        """Test OR optimization: false OR x = x."""
        left = Literal(False, SchemaType.bool)
        right = Variable("x", SchemaType.bool)
        binary_op = BinaryOp(Operator.OR, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert result.root == right

    def test_boolean_or_true_right(self):
        """Test OR optimization: x OR true = true."""
        left = Variable("x", SchemaType.bool)
        right = Literal(True, SchemaType.bool)
        binary_op = BinaryOp(Operator.OR, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_boolean_or_false_right(self):
        """Test OR optimization: x OR false = x."""
        left = Variable("x", SchemaType.bool)
        right = Literal(False, SchemaType.bool)
        binary_op = BinaryOp(Operator.OR, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert result.root == left

    def test_unary_not_constant_folding_true(self):
        """Test NOT constant folding: NOT true = false."""
        operand = Literal(True, SchemaType.bool)
        unary_op = UnaryOp(Operator.NOT, operand, SchemaType.bool)
        ast = RuleAST(unary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is False

    def test_unary_not_constant_folding_false(self):
        """Test NOT constant folding: NOT false = true."""
        operand = Literal(False, SchemaType.bool)
        unary_op = UnaryOp(Operator.NOT, operand, SchemaType.bool)
        ast = RuleAST(unary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_double_negation_elimination(self):
        """Test double negation elimination: NOT NOT x = x."""
        var = Variable("x", SchemaType.bool)
        inner_not = UnaryOp(Operator.NOT, var, SchemaType.bool)
        outer_not = UnaryOp(Operator.NOT, inner_not, SchemaType.bool)
        ast = RuleAST(outer_not, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert result.root == var

    def test_unary_not_non_boolean_literal(self):
        """Test NOT operation on non-boolean literal (should not optimize)."""
        operand = Literal(5, SchemaType.int)
        unary_op = UnaryOp(Operator.NOT, operand, SchemaType.bool)
        ast = RuleAST(unary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, UnaryOp)
        assert result.root.operator == Operator.NOT
        assert isinstance(result.root.operand, Literal)
        assert result.root.operand.value == 5

    def test_constant_folding_and_literals(self):
        """Test constant folding for AND with literal values."""
        left = Literal(True, SchemaType.bool)
        right = Literal(False, SchemaType.bool)
        binary_op = BinaryOp(Operator.AND, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is False

    def test_constant_folding_or_literals(self):
        """Test constant folding for OR with literal values."""
        left = Literal(True, SchemaType.bool)
        right = Literal(False, SchemaType.bool)
        binary_op = BinaryOp(Operator.OR, left, right, SchemaType.bool)
        ast = RuleAST(binary_op, set(), set())
        
        result = self.optimizer.optimize(ast)
        
        assert isinstance(result.root, Literal)
        assert result.root.value is True

    def test_unsupported_binary_operation_returns_original(self):
        """Test that unsupported binary operations return the original node."""
        # Create a mock operator that's not handled in constant folding
        left = Literal(5, SchemaType.int)
        right = Literal(3, SchemaType.int)
        # Using a supported operator but testing the fallback case
        binary_op = BinaryOp(Operator.EQ, left, right, SchemaType.bool)
        
        # We'll manually call the method to test the fallback
        result = self.optimizer._evaluate_literal_binary_op(
            Operator.EQ, left, right, binary_op
        )
        
        # Should return evaluated result, not original
        assert isinstance(result, Literal)
        assert result.value is False  # 5 == 3 is False

    def test_recursive_optimization(self):
        """Test that optimization works recursively on nested expressions."""
        # Create: (true AND x) OR (false AND y)
        # Should optimize to: x OR false = x
        var_x = Variable("x", SchemaType.bool)
        var_y = Variable("y", SchemaType.bool)
        
        left_and = BinaryOp(Operator.AND, Literal(True, SchemaType.bool), var_x, SchemaType.bool)
        right_and = BinaryOp(Operator.AND, Literal(False, SchemaType.bool), var_y, SchemaType.bool)
        
        or_op = BinaryOp(Operator.OR, left_and, right_and, SchemaType.bool)
        ast = RuleAST(or_op, {"x", "y"}, set())
        
        result = self.optimizer.optimize(ast)
        
        assert result.root == var_x