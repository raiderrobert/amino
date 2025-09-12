"""Tests for amino.runtime.evaluator module."""

from unittest.mock import Mock

import pytest

from amino.runtime.evaluator import RuleEvaluator
from amino.utils.errors import RuleEvaluationError


class TestRuleEvaluator:
    """Tests for RuleEvaluator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RuleEvaluator()

    def test_init_with_no_functions(self):
        """Test evaluator initialization with no function registry."""
        evaluator = RuleEvaluator()
        assert evaluator.function_registry == {}

    def test_init_with_functions(self):
        """Test evaluator initialization with function registry."""
        functions = {"test_func": lambda x: x > 0}
        evaluator = RuleEvaluator(functions)
        assert evaluator.function_registry == functions

    def test_evaluate_single_success(self):
        """Test successful single rule evaluation."""
        # Create a mock compiled rule
        mock_rule = Mock()
        mock_rule.rule_id = "test_rule"
        mock_rule.evaluate.return_value = True

        data = {"value": 10}
        result = self.evaluator.evaluate_single(mock_rule, data)

        assert result is True
        mock_rule.evaluate.assert_called_once_with(data, {})

    def test_evaluate_single_with_functions(self):
        """Test single rule evaluation with function registry."""
        functions = {"test_func": lambda x: x > 0}
        evaluator = RuleEvaluator(functions)

        mock_rule = Mock()
        mock_rule.rule_id = "test_rule"
        mock_rule.evaluate.return_value = True

        data = {"value": 10}
        result = evaluator.evaluate_single(mock_rule, data)

        assert result is True
        mock_rule.evaluate.assert_called_once_with(data, functions)

    def test_evaluate_single_failure(self):
        """Test single rule evaluation that raises an exception."""
        mock_rule = Mock()
        mock_rule.rule_id = "test_rule"
        mock_rule.evaluate.side_effect = ValueError("Test error")

        data = {"value": 10}

        with pytest.raises(RuleEvaluationError) as exc_info:
            self.evaluator.evaluate_single(mock_rule, data)

        assert "Error evaluating rule test_rule" in str(exc_info.value)
        assert "Test error" in str(exc_info.value)

    def test_evaluate_batch_success(self):
        """Test successful batch evaluation."""
        # Create mock rules
        rule1 = Mock()
        rule1.rule_id = "rule1"
        rule1.evaluate.return_value = True

        rule2 = Mock()
        rule2.rule_id = "rule2"
        rule2.evaluate.return_value = False

        rules = [rule1, rule2]
        data_list = [{"value": 10}, {"value": 5}]

        results = self.evaluator.evaluate_batch(rules, data_list)

        expected = [[("rule1", True), ("rule2", False)], [("rule1", True), ("rule2", False)]]
        assert results == expected

    def test_evaluate_batch_with_error(self):
        """Test batch evaluation with rule errors."""
        # Create mock rules where one fails
        rule1 = Mock()
        rule1.rule_id = "rule1"
        rule1.evaluate.return_value = True

        rule2 = Mock()
        rule2.rule_id = "rule2"
        rule2.evaluate.side_effect = ValueError("Test error")

        rules = [rule1, rule2]
        data_list = [{"value": 10}]

        results = self.evaluator.evaluate_batch(rules, data_list)

        # Error should result in False
        expected = [[("rule1", True), ("rule2", False)]]
        assert results == expected

    def test_evaluate_batch_empty_rules(self):
        """Test batch evaluation with empty rules list."""
        results = self.evaluator.evaluate_batch([], [{"value": 10}])
        assert results == [[]]

    def test_evaluate_batch_empty_data(self):
        """Test batch evaluation with empty data list."""
        mock_rule = Mock()
        mock_rule.rule_id = "rule1"

        results = self.evaluator.evaluate_batch([mock_rule], [])
        assert results == []

    def test_evaluate_rules_for_data_success(self):
        """Test evaluating all rules for single data item successfully."""
        rule1 = Mock()
        rule1.rule_id = "rule1"
        rule1.evaluate.return_value = True

        rule2 = Mock()
        rule2.rule_id = "rule2"
        rule2.evaluate.return_value = False

        rules = [rule1, rule2]
        data = {"value": 10}

        results = self.evaluator.evaluate_rules_for_data(rules, data)

        expected = [("rule1", True), ("rule2", False)]
        assert results == expected

    def test_evaluate_rules_for_data_with_error(self):
        """Test evaluating rules for data with error handling."""
        rule1 = Mock()
        rule1.rule_id = "rule1"
        rule1.evaluate.return_value = True

        rule2 = Mock()
        rule2.rule_id = "rule2"
        rule2.evaluate.side_effect = ValueError("Test error")

        rules = [rule1, rule2]
        data = {"value": 10}

        results = self.evaluator.evaluate_rules_for_data(rules, data)

        expected = [("rule1", True), ("rule2", False)]
        assert results == expected

    def test_evaluate_rules_for_data_empty_rules(self):
        """Test evaluating empty rules list for data."""
        results = self.evaluator.evaluate_rules_for_data([], {"value": 10})
        assert results == []

    def test_add_function(self):
        """Test adding a function to the registry."""
        test_func = lambda x: x > 0
        self.evaluator.add_function("test_func", test_func)

        assert "test_func" in self.evaluator.function_registry
        assert self.evaluator.function_registry["test_func"] == test_func

    def test_add_function_overwrites_existing(self):
        """Test that adding a function overwrites existing one."""
        func1 = lambda x: x > 0
        func2 = lambda x: x < 0

        self.evaluator.add_function("test_func", func1)
        self.evaluator.add_function("test_func", func2)

        assert self.evaluator.function_registry["test_func"] == func2

    def test_remove_function_exists(self):
        """Test removing an existing function."""
        test_func = lambda x: x > 0
        self.evaluator.add_function("test_func", test_func)

        self.evaluator.remove_function("test_func")

        assert "test_func" not in self.evaluator.function_registry

    def test_remove_function_not_exists(self):
        """Test removing a non-existent function (should not error)."""
        # This should not raise an exception
        self.evaluator.remove_function("nonexistent_func")

        # Registry should still be empty
        assert self.evaluator.function_registry == {}

    def test_remove_function_from_populated_registry(self):
        """Test removing specific function from populated registry."""
        func1 = lambda x: x > 0
        func2 = lambda x: x < 0

        self.evaluator.add_function("func1", func1)
        self.evaluator.add_function("func2", func2)

        self.evaluator.remove_function("func1")

        assert "func1" not in self.evaluator.function_registry
        assert "func2" in self.evaluator.function_registry
        assert self.evaluator.function_registry["func2"] == func2

    def test_function_registry_isolation(self):
        """Test that function registry changes don't affect other evaluators."""
        evaluator1 = RuleEvaluator()
        evaluator2 = RuleEvaluator()

        evaluator1.add_function("test_func", lambda x: x > 0)

        assert "test_func" in evaluator1.function_registry
        assert "test_func" not in evaluator2.function_registry

    def test_evaluate_single_preserves_original_exception_chain(self):
        """Test that evaluate_single preserves the original exception in the chain."""
        mock_rule = Mock()
        mock_rule.rule_id = "test_rule"
        original_error = ValueError("Original error")
        mock_rule.evaluate.side_effect = original_error

        data = {"value": 10}

        with pytest.raises(RuleEvaluationError) as exc_info:
            self.evaluator.evaluate_single(mock_rule, data)

        # Check that the original exception is preserved in the chain
        assert exc_info.value.__cause__ is original_error
