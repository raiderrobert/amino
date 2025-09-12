"""Test main Amino API functionality."""

import pytest

import amino
from amino.types import TypeRegistry
from amino.utils.errors import RuleEvaluationError, SchemaParseError


@pytest.mark.parametrize(
    "schema_content,expected_has_eval,expected_has_compile",
    [
        ("amount: Int", True, True),
        ("amount: Int\nstate_code: Str", True, True),
        ("name: Str\nage: Int\nemail: Str", True, True),
    ],
)
def test_load_schema_from_string(schema_content, expected_has_eval, expected_has_compile):
    """Test loading schema from string content."""
    amn = amino.load_schema(schema_content)
    assert amn is not None
    assert hasattr(amn, "eval") == expected_has_eval
    assert hasattr(amn, "compile") == expected_has_compile


@pytest.mark.parametrize(
    "schema_content,rule,test_data,expected_result",
    [
        ("amount: Int", "amount > 0", {"amount": 100}, True),
        ("amount: Int", "amount > 0", {"amount": 0}, False),
        ("amount: Int", "amount >= 100", {"amount": 100}, True),
        ("amount: Int", "amount < 50", {"amount": 25}, True),
        ("amount: Int\nstate_code: Str", "amount > 0 and state_code = 'CA'", {"amount": 100, "state_code": "CA"}, True),
        (
            "amount: Int\nstate_code: Str",
            "amount > 0 and state_code = 'CA'",
            {"amount": 100, "state_code": "NY"},
            False,
        ),
        ("amount: Int\nstate_code: Str", "amount > 0 and state_code = 'CA'", {"amount": 0, "state_code": "CA"}, False),
        ("name: Str\nstatus: Str", "name = 'John'", {"name": "John", "status": "active"}, True),
        ("name: Str\nstatus: Str", "name != 'Jane'", {"name": "John", "status": "active"}, True),
        ("name: Str\nstatus: Str", "name = 'Jane'", {"name": "John", "status": "active"}, False),
        (
            "price: Float\npercentage: Float",
            "price > 10.5 and percentage < 0.5",
            {"price": 20.0, "percentage": 0.3},
            True,
        ),
        (
            "price: Float\npercentage: Float",
            "price > 10.5 and percentage < 0.5",
            {"price": 5.0, "percentage": 0.3},
            False,
        ),
        ("a: Int\nb: Int\nc: Int", "a > 0 and b > 0 or c > 0", {"a": 0, "b": 0, "c": 1}, True),
        ("a: Int\nb: Int\nc: Int", "a > 0 and (b > 0 or c > 0)", {"a": 1, "b": 0, "c": 1}, True),
    ],
)
def test_rule_evaluation(schema_content, rule, test_data, expected_result):
    """Test rule evaluation with various scenarios."""
    amn = amino.load_schema(schema_content)
    result = amn.eval(rule, test_data)
    assert result == expected_result


class TestAminoAPI:
    """Test the main Amino API for non-parametrizable tests."""

    def test_batch_compilation(self, amino_ecommerce, basic_rules, sample_ecommerce_data):
        """Test batch rule compilation and evaluation."""
        compiled = amino_ecommerce.compile(basic_rules)
        results = compiled.eval(sample_ecommerce_data)

        assert len(results) == 4
        assert results[0].id == 45
        assert set(results[0].results) == {1, 2, 3}
        assert set(results[1].results) == {1, 2}
        assert set(results[2].results) == {3}
        assert set(results[3].results) == set()

    def test_ordering_first_match(self, amino_ecommerce, ordered_rules):
        """Test first match with ordering."""
        compiled = amino_ecommerce.compile(
            ordered_rules, match={"option": "first", "key": "ordering", "ordering": "asc"}
        )

        results = compiled.eval(
            [
                {"id": 100, "amount": 100, "state_code": "CA"},
                {"id": 101, "amount": 50, "state_code": "CA"},
                {"id": 102, "amount": 50, "state_code": "NY"},
            ]
        )

        assert len(results) == 3
        assert results[0].results == [3]  # First by ordering
        assert results[1].results == [2]  # Second by ordering
        assert results[2].results == []  # No matches

    def test_function_support(self):
        """Test external function support."""
        amn = amino.load_schema("amount: Int")

        amn.add_function("min_func", min)

        amn2 = amino.load_schema("amount: Int\nmin_func: (a: Int, b: Int) -> int")
        amn2.add_function("min_func", min)
        result = amn2.eval("min_func(amount, 1000) < 1000", {"amount": 100})
        assert result is True

        assert "min_func" in amn.engine.function_registry

    def test_type_registry_integration(self):
        """Test integration with custom type registry."""
        registry = TypeRegistry()
        registry.register_type("positive_int", "Int", validator=lambda x: isinstance(x, int) and x > 0)

        amn = amino.load_schema("amount: positive_int", type_registry=registry)

        result = amn.eval("amount > 0", {"amount": 100})
        assert result is True


@pytest.mark.parametrize(
    "schema_content,rule,test_data,expected_error_type,expected_error_contains",
    [
        ("amount: Int", "amount > unknown_var", {"amount": 100}, RuleEvaluationError, "Unknown variable: unknown_var"),
        ("amount: Int\nstate_code: Str", "amount > 0", {"state_code": "CA"}, RuleEvaluationError, "amount"),
        ("amount: Int\nstate_code: Str", "state_code = 'CA'", {"amount": 100}, RuleEvaluationError, "state_code"),
    ],
)
def test_error_handling(schema_content, rule, test_data, expected_error_type, expected_error_contains):
    """Test error handling for various invalid scenarios."""
    amn = amino.load_schema(schema_content)

    with pytest.raises(expected_error_type) as excinfo:
        amn.eval(rule, test_data)
    assert expected_error_contains in str(excinfo.value)


def test_invalid_schema():
    """Test error handling for invalid schema with strict mode."""
    with pytest.raises(SchemaParseError) as exc_info:
        amino.load_schema("invalid: unknown_type", strict=True)
    assert "Unknown type" in str(exc_info.value)
