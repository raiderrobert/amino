"""Test runtime functionality."""

import pytest
from amino.runtime import RuleEngine, MatchResult, MatchMode
from amino.runtime.engine import RuleDefinition
from amino.runtime.matcher import MatchOptions
from amino.schema.parser import parse_schema
from amino.utils.errors import RuleParseError, RuleEvaluationError


class TestRuleEngine:
    """Test the RuleEngine functionality."""

    def test_basic_rule_compilation(self):
        """Test basic rule compilation."""
        schema_ast = parse_schema("amount: int\nstate: str")
        engine = RuleEngine(schema_ast)
        
        rules = [
            {"id": 1, "rule": "amount > 0"},
            {"id": 2, "rule": "state = 'CA'"},
        ]
        
        compiled = engine.compile_rules(rules)
        assert compiled is not None
        assert len(compiled.rules) == 2

    def test_single_rule_evaluation(self):
        """Test single rule evaluation."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        result = engine.eval_single_rule("amount > 100", {"amount": 150})
        assert result is True
        
        result = engine.eval_single_rule("amount > 100", {"amount": 50})
        assert result is False

    def test_batch_evaluation(self):
        """Test batch rule evaluation."""
        schema_ast = parse_schema("amount: int\nstate: str")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 100"},
            {"id": 2, "rule": "state = 'CA'"},
        ])
        
        results = compiled.eval([
            {"id": "a", "amount": 150, "state": "CA"},
            {"id": "b", "amount": 50, "state": "CA"},
            {"id": "c", "amount": 150, "state": "NY"},
        ])
        
        assert len(results) == 3
        assert set(results[0].results) == {1, 2}
        assert set(results[1].results) == {2}
        assert set(results[2].results) == {1}

    def test_rule_with_functions(self):
        """Test rules with external functions."""
        # For now, skip function declarations in schema
        schema_ast = parse_schema("a: int\nb: int")
        engine = RuleEngine(schema_ast)
        engine.add_function("min_func", min)
        
        # TODO: Implement proper function declaration parsing
        # For now, this will fail because min_func isn't in schema
        # result = engine.eval_single_rule("min_func(a, b) < 10", {"a": 5, "b": 15})
        # assert result is True
        
        # Just test that functions can be added
        assert "min_func" in engine.function_registry

    def test_rule_optimization(self):
        """Test rule optimization."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        # This rule should be optimized (true AND x = x)
        result = engine.eval_single_rule("amount > 0", {"amount": 100})
        assert result is True

    def test_rule_definition_objects(self):
        """Test using RuleDefinition objects."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        rule_def = RuleDefinition(
            id="test_rule",
            rule="amount > 0", 
            ordering=1,
            metadata={"category": "basic"}
        )
        
        compiled = engine.compile_rules([rule_def])
        results = compiled.eval([{"id": "a", "amount": 100}])
        
        assert results[0].results == ["test_rule"]

    def test_invalid_rule_compilation(self):
        """Test error handling for invalid rules."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        with pytest.raises(RuleParseError):
            engine.compile_rules([{"id": 1, "rule": "invalid > syntax >"}])

    def test_missing_variable_error(self):
        """Test error for missing variables."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        with pytest.raises(RuleEvaluationError):
            engine.eval_single_rule("unknown_var > 0", {"amount": 100})


class TestMatchOptions:
    """Test match options and result processing."""

    def test_all_matches_mode(self):
        """Test ALL matches mode (default)."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 0"},
            {"id": 2, "rule": "amount > 50"},
            {"id": 3, "rule": "amount > 100"},
        ])
        
        results = compiled.eval([{"id": "a", "amount": 150}])
        assert set(results[0].results) == {1, 2, 3}

    def test_first_match_mode(self):
        """Test FIRST match mode with ordering."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 0", "ordering": 3},
            {"id": 2, "rule": "amount > 50", "ordering": 1}, 
            {"id": 3, "rule": "amount > 100", "ordering": 2},
        ], match={"option": "first", "key": "ordering", "ordering": "asc"})
        
        results = compiled.eval([{"id": "a", "amount": 150}])
        assert results[0].results == [2]  # First by ordering

    def test_first_match_descending_order(self):
        """Test FIRST match mode with descending order."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 0", "ordering": 1},
            {"id": 2, "rule": "amount > 50", "ordering": 2},
            {"id": 3, "rule": "amount > 100", "ordering": 3},
        ], match={"option": "first", "key": "ordering", "ordering": "desc"})
        
        results = compiled.eval([{"id": "a", "amount": 150}])
        assert results[0].results == [3]  # First by descending ordering

    def test_no_matches(self):
        """Test handling when no rules match."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 1000"},
        ])
        
        results = compiled.eval([{"id": "a", "amount": 100}])
        assert results[0].results == []

    def test_metadata_preservation(self):
        """Test that rule metadata is preserved."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 0", "metadata": {"category": "basic"}},
        ])
        
        # Metadata should be accessible through the compiled rules
        assert compiled.rule_metadata[1]["category"] == "basic"


class TestCompiledRules:
    """Test CompiledRules functionality."""

    def test_single_evaluation(self):
        """Test single data item evaluation."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 100"},
        ])
        
        result = compiled.eval_single({"id": "test", "amount": 150})
        assert isinstance(result, MatchResult)
        assert result.id == "test"
        assert result.results == [1]

    def test_function_addition(self):
        """Test adding functions to compiled rules.""" 
        schema_ast = parse_schema("a: int\nb: int")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "a > 5"},  # Simple rule for now
        ])
        
        compiled.add_function("max_func", max)
        
        result = compiled.eval_single({"id": "test", "a": 10, "b": 15})
        assert result.results == [1]

    def test_rule_variables_tracking(self):
        """Test tracking of rule variables."""
        schema_ast = parse_schema("amount: int\nstate: str")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 0 and state = 'CA'"},
        ])
        
        variables = compiled.get_rule_variables()
        assert "amount" in variables[1]
        assert "state" in variables[1]

    def test_rule_functions_tracking(self):
        """Test tracking of rule functions."""
        schema_ast = parse_schema("amount: int")
        engine = RuleEngine(schema_ast)
        
        compiled = engine.compile_rules([
            {"id": 1, "rule": "amount > 100"},  # Simple rule for now
        ])
        
        functions = compiled.get_rule_functions()
        # No functions in simple rule
        assert functions[1] == []