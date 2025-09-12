"""Basic integration tests for amino functionality."""

import pytest

import amino
from amino.schema.parser import SchemaParser


def test_amino_import():
    """Test amino module import."""
    assert hasattr(amino, "load_schema")
    assert hasattr(amino, "Schema")


def test_schema_parser_basic():
    """Test basic schema parser functionality."""
    parser = SchemaParser("amount: Int")
    ast = parser.parse()

    assert len(ast.fields) == 1
    assert ast.fields[0].name == "amount"
    assert ast.fields[0].field_type.value == "Int"


@pytest.mark.parametrize(
    "schema_content,rule,test_data,expected_result",
    [
        ("amount: Int\nstate_code: Str", "amount > 0", {"amount": 100, "state_code": "CA"}, True),
        ("amount: Int\nstate_code: Str", 'amount > 0 and state_code = "CA"', {"amount": 100, "state_code": "CA"}, True),
        ("amount: Int\nstate_code: Str", 'amount > 0 and state_code = "CA"', {"amount": 0, "state_code": "CA"}, False),
    ],
)
def test_integration_basic_usage(schema_content, rule, test_data, expected_result):
    """Test basic amino usage integration."""
    amn = amino.load_schema(schema_content)
    result = amn.eval(rule, test_data)
    assert result == expected_result


def test_integration_batch_processing():
    """Test batch processing integration like README examples."""
    amn = amino.load_schema("amount: Int\nstate_code: Str")
    compiled = amn.compile(
        [
            {"id": 1, "rule": "amount > 0 and state_code = 'CA'"},
            {"id": 2, "rule": "amount > 10 and state_code = 'CA'"},
            {"id": 3, "rule": "amount >= 100"},
        ]
    )

    results = compiled.eval(
        [
            {"id": 45, "amount": 100, "state_code": "CA"},
            {"id": 46, "amount": 50, "state_code": "CA"},
            {"id": 47, "amount": 100, "state_code": "NY"},
            {"id": 48, "amount": 10, "state_code": "NY"},
        ]
    )

    assert len(results) == 4
    assert results[0].id == 45
    assert set(results[0].results) == {1, 2, 3}
    assert set(results[1].results) == {1, 2}
    assert set(results[2].results) == {3}
    assert set(results[3].results) == set()


def test_integration_ordering():
    """Test ordering feature integration."""
    amn = amino.load_schema("amount: Int\nstate_code: Str")
    compiled = amn.compile(
        [
            {"id": 1, "rule": "amount > 0 and state_code = 'CA'", "ordering": 3},
            {"id": 2, "rule": "amount > 10 and state_code = 'CA'", "ordering": 2},
            {"id": 3, "rule": "amount >= 100", "ordering": 1},
        ],
        match={"option": "first", "key": "ordering", "ordering": "asc"},
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
