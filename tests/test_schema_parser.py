"""
Tests for the schema parser.
"""

import pytest
from amino.parser.schema import parse_schema, SchemaParseError
from amino.types.base import PrimitiveType, TypeKind, StructType, ListType

def test_basic_types():
    """Test parsing of basic type declarations"""
    schema = """
    amount: int
    name: str
    active: bool
    score: float
    """
    
    types = parse_schema(schema)
    assert types['amount'] == PrimitiveType(TypeKind.INT)
    assert types['name'] == PrimitiveType(TypeKind.STR)
    assert types['active'] == PrimitiveType(TypeKind.BOOL)
    assert types['score'] == PrimitiveType(TypeKind.FLOAT)

def test_struct_type():
    """Test parsing of struct type declarations"""
    schema = """
    struct person {
        name: str,
        age: int,
    }
    """
    
    types = parse_schema(schema)
    assert isinstance(types['person'], StructType)
    assert types['person'].name == 'person'
    assert types['person'].fields['name'] == PrimitiveType(TypeKind.STR)
    assert types['person'].fields['age'] == PrimitiveType(TypeKind.INT)

def test_list_type():
    """Test parsing of list type declarations"""
    schema = """
    scores: list[int]
    names: list[str]
    """
    
    types = parse_schema(schema)
    assert isinstance(types['scores'], ListType)
    assert types['scores'].element_type == PrimitiveType(TypeKind.INT)
    assert isinstance(types['names'], ListType)
    assert types['names'].element_type == PrimitiveType(TypeKind.STR)

def test_comments():
    """Test handling of comments"""
    schema = """
    # This is a comment
    amount: int  # This is an inline comment
    # Another comment
    name: str
    """
    
    types = parse_schema(schema)
    assert types['amount'] == PrimitiveType(TypeKind.INT)
    assert types['name'] == PrimitiveType(TypeKind.STR)

def test_invalid_type():
    """Test handling of invalid type declarations"""
    schema = """
    amount: invalid_type
    """
    
    with pytest.raises(SchemaParseError):
        parse_schema(schema)

def test_invalid_syntax():
    """Test handling of invalid syntax"""
    schema = """
    amount: int str  # Invalid: multiple types
    """
    
    with pytest.raises(SchemaParseError):
        parse_schema(schema)

def test_complex_schema():
    """Test parsing of a complex schema with multiple features"""
    schema = """
    # User information
    struct user {
        name: str,
        age: int,
        active: bool,
    }

    # Scores and metrics
    scores: list[float]
    top_score: float

    # System settings
    enabled: bool
    config: str
    """
    
    types = parse_schema(schema)
    
    # Check struct
    assert isinstance(types['user'], StructType)
    assert types['user'].fields['name'] == PrimitiveType(TypeKind.STR)
    assert types['user'].fields['age'] == PrimitiveType(TypeKind.INT)
    assert types['user'].fields['active'] == PrimitiveType(TypeKind.BOOL)
    
    # Check list
    assert isinstance(types['scores'], ListType)
    assert types['scores'].element_type == PrimitiveType(TypeKind.FLOAT)
    
    # Check basic types
    assert types['top_score'] == PrimitiveType(TypeKind.FLOAT)
    assert types['enabled'] == PrimitiveType(TypeKind.BOOL)
    assert types['config'] == PrimitiveType(TypeKind.STR)