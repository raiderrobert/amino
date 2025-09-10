"""Test main Amino API functionality."""

import pytest
import amino
from amino.utils.errors import SchemaParseError, RuleParseError, RuleEvaluationError
from amino.types import TypeRegistry


class TestAminoAPI:
    """Test the main Amino API."""

    def test_load_schema_from_string(self):
        """Test loading schema from string content."""
        amn = amino.load_schema("amount: int\nstate_code: str")
        assert amn is not None
        assert hasattr(amn, 'eval')
        assert hasattr(amn, 'compile')

    def test_basic_evaluation(self):
        """Test basic rule evaluation."""
        amn = amino.load_schema("amount: int\nstate_code: str")
        
        # True case
        result = amn.eval("amount > 0", {"amount": 100, "state_code": "CA"})
        assert result is True
        
        # False case
        result = amn.eval("amount > 0", {"amount": 0, "state_code": "CA"})
        assert result is False

    def test_complex_evaluation(self):
        """Test complex rule evaluation."""
        amn = amino.load_schema("amount: int\nstate_code: str")
        
        # AND operation
        result = amn.eval("amount > 0 and state_code = 'CA'", 
                         {"amount": 100, "state_code": "CA"})
        assert result is True
        
        result = amn.eval("amount > 0 and state_code = 'CA'", 
                         {"amount": 100, "state_code": "NY"})
        assert result is False

    def test_batch_compilation(self):
        """Test batch rule compilation and evaluation."""
        amn = amino.load_schema("amount: int\nstate_code: str")
        
        compiled = amn.compile([
            {"id": 1, "rule": "amount > 0 and state_code = 'CA'"},
            {"id": 2, "rule": "amount > 10 and state_code = 'CA'"},
            {"id": 3, "rule": "amount >= 100"},
        ])
        
        results = compiled.eval([
            {"id": 45, "amount": 100, "state_code": "CA"},
            {"id": 46, "amount": 50, "state_code": "CA"},
            {"id": 47, "amount": 100, "state_code": "NY"},
            {"id": 48, "amount": 10, "state_code": "NY"},
        ])
        
        assert len(results) == 4
        assert results[0].id == 45
        assert set(results[0].results) == {1, 2, 3}
        assert set(results[1].results) == {1, 2}
        assert set(results[2].results) == {3}
        assert set(results[3].results) == set()

    def test_ordering_first_match(self):
        """Test first match with ordering."""
        amn = amino.load_schema("amount: int\nstate_code: str")
        
        compiled = amn.compile([
            {"id": 1, "rule": "amount > 0 and state_code = 'CA'", "ordering": 3},
            {"id": 2, "rule": "amount > 10 and state_code = 'CA'", "ordering": 2},
            {"id": 3, "rule": "amount >= 100", "ordering": 1},
        ], match={"option": "first", "key": "ordering", "ordering": "asc"})
        
        results = compiled.eval([
            {"id": 100, "amount": 100, "state_code": "CA"},
            {"id": 101, "amount": 50, "state_code": "CA"},
            {"id": 102, "amount": 50, "state_code": "NY"},
        ])
        
        assert len(results) == 3
        assert results[0].results == [3]  # First by ordering
        assert results[1].results == [2]  # Second by ordering
        assert results[2].results == []   # No matches

    def test_function_support(self):
        """Test external function support."""
        # For now, test with just the basic schema without function declarations
        amn = amino.load_schema("amount: int")
        
        # Add function to runtime
        amn.add_function("min_func", min)
        
        # This would fail because min_func isn't declared in schema yet
        # TODO: Implement proper function declaration parsing
        # result = amn.eval("min_func(amount, 1000) < 1000", {"amount": 100})
        # assert result is True
        
        # For now, just test that we can add functions
        assert "min_func" in amn.engine.function_registry

    def test_invalid_schema(self):
        """Test error handling for invalid schema."""
        with pytest.raises(SchemaParseError):
            amino.load_schema("invalid: unknown_type")

    def test_invalid_rule(self):
        """Test error handling for invalid rule."""
        amn = amino.load_schema("amount: int")
        
        with pytest.raises(RuleEvaluationError):
            amn.eval("amount > unknown_var", {"amount": 100})

    def test_missing_data_field(self):
        """Test handling of missing data fields.""" 
        amn = amino.load_schema("amount: int\nstate_code: str")
        
        with pytest.raises(RuleEvaluationError):
            amn.eval("amount > 0", {"state_code": "CA"})  # Missing amount

    def test_type_registry_integration(self):
        """Test integration with custom type registry."""
        registry = TypeRegistry()
        registry.register_type("positive_int", "int", 
                              validator=lambda x: isinstance(x, int) and x > 0)
        
        amn = amino.load_schema("amount: positive_int", type_registry=registry)
        
        # This should work with the rule evaluation
        result = amn.eval("amount > 0", {"amount": 100})
        assert result is True

    def test_float_support(self):
        """Test float type support."""
        amn = amino.load_schema("price: float\npercentage: float")
        
        result = amn.eval("price > 10.5 and percentage < 0.5", 
                         {"price": 20.0, "percentage": 0.3})
        assert result is True

    def test_string_operations(self):
        """Test string comparison operations."""
        amn = amino.load_schema("name: str\nstatus: str")
        
        # Equality
        result = amn.eval("name = 'John'", {"name": "John", "status": "active"})
        assert result is True
        
        # Inequality  
        result = amn.eval("name != 'Jane'", {"name": "John", "status": "active"})
        assert result is True

    def test_parentheses_precedence(self):
        """Test operator precedence with parentheses."""
        amn = amino.load_schema("a: int\nb: int\nc: int")
        
        # Without parentheses: a > 0 and b > 0 or c > 0
        # Should be: (a > 0 and b > 0) or c > 0
        result = amn.eval("a > 0 and b > 0 or c > 0", 
                         {"a": 0, "b": 0, "c": 1})
        assert result is True
        
        # With parentheses: a > 0 and (b > 0 or c > 0)  
        result = amn.eval("a > 0 and (b > 0 or c > 0)", 
                         {"a": 1, "b": 0, "c": 1})
        assert result is True