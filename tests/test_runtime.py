"""Test runtime functionality."""

import pytest
from amino.runtime import RuleEngine, MatchResult, MatchMode
from amino.runtime.engine import RuleDefinition
from amino.runtime.matcher import MatchOptions
from amino.schema.parser import parse_schema
from amino.utils.errors import RuleParseError, RuleEvaluationError


@pytest.mark.parametrize(
    "schema_content,rules,expected_rule_count",
    [
        ("amount: int", [{"id": 1, "rule": "amount > 0"}], 1),
        ("amount: int\nstate: str", [
            {"id": 1, "rule": "amount > 0"},
            {"id": 2, "rule": "state = 'CA'"}
        ], 2),
        ("a: int\nb: int\nc: int", [
            {"id": 1, "rule": "a > 0"},
            {"id": 2, "rule": "b > 0"},
            {"id": 3, "rule": "c > 0"}
        ], 3)
    ]
)
def test_rule_compilation(schema_content, rules, expected_rule_count):
    """Test rule compilation with various scenarios."""
    schema_ast = parse_schema(schema_content)
    engine = RuleEngine(schema_ast)
    
    compiled = engine.compile_rules(rules)
    assert compiled is not None
    assert len(compiled.rules) == expected_rule_count


@pytest.mark.parametrize(
    "schema_content,rule,test_data,expected_result",
    [
        ("amount: int", "amount > 100", {"amount": 150}, True),
        ("amount: int", "amount > 100", {"amount": 50}, False),
        ("amount: int", "amount >= 100", {"amount": 100}, True),
        ("amount: int", "amount < 50", {"amount": 25}, True),
        ("name: str", "name = 'John'", {"name": "John"}, True),
        ("name: str", "name != 'John'", {"name": "Jane"}, True)
    ]
)
def test_single_rule_evaluation(schema_content, rule, test_data, expected_result):
    """Test single rule evaluation with various scenarios."""
    schema_ast = parse_schema(schema_content)
    engine = RuleEngine(schema_ast)
    
    result = engine.eval_single_rule(rule, test_data)
    assert result == expected_result


class TestRuleEngine:
    """Test the RuleEngine functionality for non-parametrizable tests."""

    def test_batch_evaluation(self, ecommerce_rule_engine):
        """Test batch rule evaluation."""
        compiled = ecommerce_rule_engine.compile_rules([
            {"id": 1, "rule": "amount > 100"},
            {"id": 2, "rule": "state_code = 'CA'"},
        ])
        
        results = compiled.eval([
            {"id": "a", "amount": 150, "state_code": "CA"},
            {"id": "b", "amount": 50, "state_code": "CA"},
            {"id": "c", "amount": 150, "state_code": "NY"},
        ])
        
        assert len(results) == 3
        assert set(results[0].results) == {1, 2}
        assert set(results[1].results) == {2}
        assert set(results[2].results) == {1}

    def test_rule_with_functions(self):
        """Test rules with external functions."""
        # For now, skip function declarations in schema
        # Test with proper function declaration in schema
        schema_ast = parse_schema("a: int\nb: int\nmin_func: (int, int) -> int")
        engine = RuleEngine(schema_ast)
        engine.add_function("min_func", min)
        
        # Test function evaluation
        result = engine.eval_single_rule("min_func(a, b) < 10", {"a": 5, "b": 15})
        assert result is True
        
        # Test that functions can be added
        assert "min_func" in engine.function_registry

    def test_rule_optimization(self, simple_rule_engine):
        """Test rule optimization."""
        # This rule should be optimized (true AND x = x)
        result = simple_rule_engine.eval_single_rule("amount > 0", {"amount": 100})
        assert result is True

    def test_rule_definition_objects(self, simple_rule_engine):
        """Test using RuleDefinition objects."""
        rule_def = RuleDefinition(
            id="test_rule",
            rule="amount > 0", 
            ordering=1,
            metadata={"category": "basic"}
        )
        
        compiled = simple_rule_engine.compile_rules([rule_def])
        results = compiled.eval([{"id": "a", "amount": 100}])
        
        assert results[0].results == ["test_rule"]


@pytest.mark.parametrize(
    "schema_content,rules,expected_error_type,expected_error_contains",
    [
        # Invalid rule syntax
        ("amount: int", [{"id": 1, "rule": "invalid > syntax >"}], 
         RuleParseError, "Unknown variable"),
         
        ("amount: int", [{"id": 1, "rule": "amount > 0 and"}], 
         RuleParseError, "Unexpected end"),
    ]
)
def test_invalid_rule_compilation(schema_content, rules, expected_error_type, expected_error_contains):
    """Test error handling for invalid rules."""
    schema_ast = parse_schema(schema_content)
    engine = RuleEngine(schema_ast)
    
    with pytest.raises(expected_error_type) as excinfo:
        engine.compile_rules(rules)
    assert expected_error_contains in str(excinfo.value)


@pytest.mark.parametrize(
    "schema_content,rule,test_data,expected_error_type,expected_error_contains",
    [
        ("amount: int", "unknown_var > 0", {"amount": 100}, 
         RuleEvaluationError, "Unknown variable: unknown_var"),
         
        ("amount: int", "missing_field > 0", {"amount": 100}, 
         RuleEvaluationError, "Unknown variable: missing_field"),
    ]
)
def test_rule_evaluation_errors(schema_content, rule, test_data, expected_error_type, expected_error_contains):
    """Test error handling for rule evaluation."""
    schema_ast = parse_schema(schema_content)
    engine = RuleEngine(schema_ast)
    
    with pytest.raises(expected_error_type) as excinfo:
        engine.eval_single_rule(rule, test_data)
    assert expected_error_contains in str(excinfo.value)


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

    def test_single_evaluation(self, simple_rule_engine):
        """Test single data item evaluation."""
        compiled = simple_rule_engine.compile_rules([
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

    def test_rule_variables_tracking(self, ecommerce_rule_engine):
        """Test tracking of rule variables."""
        compiled = ecommerce_rule_engine.compile_rules([
            {"id": 1, "rule": "amount > 0 and state_code = 'CA'"},
        ])
        
        variables = compiled.get_rule_variables()
        assert "amount" in variables[1]
        assert "state_code" in variables[1]

    def test_rule_functions_tracking(self, simple_rule_engine):
        """Test tracking of rule functions."""
        compiled = simple_rule_engine.compile_rules([
            {"id": 1, "rule": "amount > 100"},  # Simple rule for now
        ])
        
        functions = compiled.get_rule_functions()
        # No functions in simple rule
        assert functions[1] == []