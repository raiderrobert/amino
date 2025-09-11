"""Shared pytest fixtures for the amino test suite."""

import pytest
import amino
from amino.schema.parser import parse_schema
from amino.runtime import RuleEngine
from amino.types import TypeRegistry, register_builtin_types
from amino.types import TypeValidator


# Schema Fixtures
@pytest.fixture
def simple_int_schema():
    """Simple schema with just an integer field."""
    return parse_schema("amount: int")


@pytest.fixture
def ecommerce_schema():
    """E-commerce schema with amount and state_code fields."""
    return parse_schema("amount: int\nstate_code: str")


@pytest.fixture
def person_schema():
    """Schema with name and age fields."""
    return parse_schema("name: str\nage: int")


@pytest.fixture
def person_struct_schema():
    """Schema with person struct definition."""
    return parse_schema("""
    struct person {
        name: str,
        age: int
    }
    """)


@pytest.fixture
def advanced_schema():
    """Complex schema with struct, functions, and constraints."""
    return parse_schema("""
    struct applicant {
        name: str,
        age: int,
        tags: list[str]
    }
    
    MIN_AGE: int = 18
    validate_eligibility: (applicant, int) -> bool
    """)


# RuleEngine Fixtures
@pytest.fixture
def simple_rule_engine(simple_int_schema):
    """RuleEngine with simple integer schema."""
    return RuleEngine(simple_int_schema)


@pytest.fixture
def ecommerce_rule_engine(ecommerce_schema):
    """RuleEngine with e-commerce schema."""
    return RuleEngine(ecommerce_schema)


@pytest.fixture
def person_rule_engine(person_schema):
    """RuleEngine with person schema."""
    return RuleEngine(person_schema)


# TypeRegistry Fixtures
@pytest.fixture
def type_registry():
    """Empty TypeRegistry."""
    return TypeRegistry()


@pytest.fixture
def populated_type_registry():
    """TypeRegistry with builtin types registered."""
    registry = TypeRegistry()
    register_builtin_types(registry)
    return registry


@pytest.fixture
def custom_type_registry():
    """TypeRegistry with custom positive_int type."""
    registry = TypeRegistry()
    registry.register_type("positive_int", "int", 
                          validator=lambda x: isinstance(x, int) and x > 0)
    return registry


# Amino Instance Fixtures
@pytest.fixture
def amino_simple():
    """Amino instance with simple integer schema."""
    return amino.load_schema("amount: int")


@pytest.fixture
def amino_ecommerce():
    """Amino instance with e-commerce schema."""
    return amino.load_schema("amount: int\nstate_code: str")


@pytest.fixture
def amino_person():
    """Amino instance with person schema."""
    return amino.load_schema("name: str\nage: int")


# TypeValidator Fixtures
@pytest.fixture
def type_validator(ecommerce_schema):
    """TypeValidator with e-commerce schema."""
    return TypeValidator(ecommerce_schema)


@pytest.fixture
def person_type_validator(person_schema):
    """TypeValidator with person schema."""
    return TypeValidator(person_schema)


# Test Data Fixtures
@pytest.fixture
def sample_ecommerce_data():
    """Sample e-commerce test data for batch processing."""
    return [
        {"id": 45, "amount": 100, "state_code": "CA"},
        {"id": 46, "amount": 50, "state_code": "CA"},
        {"id": 47, "amount": 100, "state_code": "NY"},
        {"id": 48, "amount": 10, "state_code": "NY"}
    ]


@pytest.fixture
def basic_rules():
    """Basic rule definitions for e-commerce scenarios."""
    return [
        {"id": 1, "rule": "amount > 0 and state_code = 'CA'"},
        {"id": 2, "rule": "amount > 10 and state_code = 'CA'"},
        {"id": 3, "rule": "amount >= 100"}
    ]


@pytest.fixture
def ordered_rules():
    """Rule definitions with ordering for first-match tests."""
    return [
        {"id": 1, "rule": "amount > 0 and state_code = 'CA'", "ordering": 3},
        {"id": 2, "rule": "amount > 10 and state_code = 'CA'", "ordering": 2},
        {"id": 3, "rule": "amount >= 100", "ordering": 1}
    ]