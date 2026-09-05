"""Shared pytest fixtures for the amino test suite."""

import pytest

from amino.schema.parser import parse_schema


@pytest.fixture
def simple_int_schema():
    """Simple schema with just an integer field."""
    return parse_schema("amount: Int")


@pytest.fixture
def ecommerce_schema():
    """E-commerce schema with amount and state_code fields."""
    return parse_schema("amount: Int\nstate_code: Str")


@pytest.fixture
def person_schema():
    """Schema with name and age fields."""
    return parse_schema("name: Str\nage: Int")


@pytest.fixture
def person_struct_schema():
    """Schema with person struct definition."""
    return parse_schema("""
    struct person {
        name: Str,
        age: Int
    }
    """)


@pytest.fixture
def sample_ecommerce_data():
    """Sample e-commerce test data for batch processing."""
    return [
        {"id": 45, "amount": 100, "state_code": "CA"},
        {"id": 46, "amount": 50, "state_code": "CA"},
        {"id": 47, "amount": 100, "state_code": "NY"},
        {"id": 48, "amount": 10, "state_code": "NY"},
    ]


@pytest.fixture
def basic_rules():
    """Basic rule definitions for e-commerce scenarios."""
    return [
        {"id": 1, "rule": "amount > 0 and state_code = 'CA'"},
        {"id": 2, "rule": "amount > 10 and state_code = 'CA'"},
        {"id": 3, "rule": "amount >= 100"},
    ]


@pytest.fixture
def ordered_rules():
    """Rule definitions with ordering for first-match tests."""
    return [
        {"id": 1, "rule": "amount > 0 and state_code = 'CA'", "ordering": 3},
        {"id": 2, "rule": "amount > 10 and state_code = 'CA'", "ordering": 2},
        {"id": 3, "rule": "amount >= 100", "ordering": 1},
    ]
