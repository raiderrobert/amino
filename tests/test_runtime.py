"""
Tests for the runtime functionality.
"""

import pytest
from amino.core import Amino
from amino.types.base import PrimitiveType, TypeKind, TypeError


def test_simple_evaluation():
    """Test simple rule evaluation"""
    # Create Amino instance with basic schema
    schema_types = {
        'amount': PrimitiveType(TypeKind.INT),
        'state_code': PrimitiveType(TypeKind.STR),
        'bool': PrimitiveType(TypeKind.BOOL),
    }
    amn = Amino(schema_types)
    
    # Test simple rule
    data = {
        "amount": 100,
        "state_code": "CA"
    }
    
    assert amn.eval("amount > 0", data) == True
    assert amn.eval("amount < 0", data) == False
    assert amn.eval("state_code = 'CA'", data) == True
    assert amn.eval("state_code = 'NY'", data) == False
    assert amn.eval("amount > 0 and state_code = 'CA'", data) == True


def test_multiple_rules():
    """Test evaluation of multiple rules"""
    schema_types = {
        'amount': PrimitiveType(TypeKind.INT),
        'state_code': PrimitiveType(TypeKind.STR),
        'bool': PrimitiveType(TypeKind.BOOL),
    }
    amn = Amino(schema_types)
    
    rules = [
        {
            'id': 1,
            'rule': "amount > 0 and state_code = 'CA'",
            'ordering': 3
        },
        {
            'id': 2,
            'rule': "amount > 10 and state_code = 'CA'",
            'ordering': 2
        },
        {
            'id': 3,
            'rule': "amount >= 100",
            'ordering': 1
        }
    ]
    
    match_config = {
        'option': 'first',
        'key': 'ordering',
        'ordering': 'asc'
    }
    
    compiled = amn.compile(rules, match_config)
    
    datasets = [
        {'id': 45, 'amount': 100, 'state_code': 'CA'},
        {'id': 46, 'amount': 50, 'state_code': 'CA'},
        {'id': 47, 'amount': 100, 'state_code': 'NY'},
    ]
    
    results = compiled.eval(datasets)
    
    # Check results
    assert results[0]['id'] == 45
    assert results[0]['results'] == [3]  # Only rule 3 due to first match and ordering
    
    assert results[1]['id'] == 46
    assert results[1]['results'] == [2]  # Rule 2 matches first
    
    assert results[2]['id'] == 47
    assert results[2]['results'] == [3]  # Only rule 3 matches


def test_match_all():
    """Test evaluation with match all configuration"""
    schema_types = {
        'amount': PrimitiveType(TypeKind.INT),
        'state_code': PrimitiveType(TypeKind.STR),
        'bool': PrimitiveType(TypeKind.BOOL),
    }
    amn = Amino(schema_types)
    
    rules = [
        {'id': 1, 'rule': "amount > 0"},
        {'id': 2, 'rule': "amount >= 50"},
        {'id': 3, 'rule': "amount >= 100"},
    ]
    
    compiled = amn.compile(rules)  # Default is match all
    
    datasets = [
        {'id': 1, 'amount': 100},
        {'id': 2, 'amount': 50},
        {'id': 3, 'amount': 0},
    ]
    
    results = compiled.eval(datasets)
    
    # Check results
    assert results[0]['id'] == 1
    assert set(results[0]['results']) == {1, 2, 3}  # All rules match
    
    assert results[1]['id'] == 2
    assert set(results[1]['results']) == {1, 2}  # Rules 1 and 2 match
    
    assert results[2]['id'] == 3
    assert results[2]['results'] == []  # No rules match


def test_type_errors():
    """Test handling of type errors"""
    schema_types = {
        'amount': PrimitiveType(TypeKind.INT),
        'state_code': PrimitiveType(TypeKind.STR),
        'bool': PrimitiveType(TypeKind.BOOL),
    }
    amn = Amino(schema_types)
    
    data = {
        "amount": 100,
        "state_code": "CA"
    }
    
    # Test comparing different types
    with pytest.raises(TypeError):
        amn.eval("amount = state_code", data)  # Should raise TypeError
    
    # Test unknown identifier
    with pytest.raises(TypeError):
        amn.eval("unknown > 0", data)  # Should raise TypeError