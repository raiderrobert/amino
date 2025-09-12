"""Tests for amino.utils.helpers module."""

import pytest
from amino.utils.helpers import flatten_dict, is_reserved_name


class TestFlattenDict:
    """Tests for flatten_dict function."""

    def test_empty_dict(self):
        """Test flattening an empty dictionary."""
        result = flatten_dict({})
        assert result == {}

    def test_flat_dict(self):
        """Test flattening an already flat dictionary."""
        data = {"a": 1, "b": 2, "c": "hello"}
        result = flatten_dict(data)
        expected = {"a": 1, "b": 2, "c": "hello"}
        assert result == expected

    def test_nested_dict(self):
        """Test flattening a nested dictionary."""
        data = {
            "user": {"name": "John", "age": 30},
            "config": {"debug": True, "version": "1.0"}
        }
        result = flatten_dict(data)
        expected = {
            "user.name": "John",
            "user.age": 30,
            "config.debug": True,
            "config.version": "1.0"
        }
        assert result == expected

    def test_deeply_nested_dict(self):
        """Test flattening a deeply nested dictionary."""
        data = {
            "level1": {
                "level2": {
                    "level3": {"value": "deep"}
                }
            }
        }
        result = flatten_dict(data)
        expected = {"level1.level2.level3.value": "deep"}
        assert result == expected

    def test_mixed_types(self):
        """Test flattening with mixed value types."""
        data = {
            "string": "hello",
            "number": 42,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "nested": {"inner": "value"}
        }
        result = flatten_dict(data)
        expected = {
            "string": "hello",
            "number": 42,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "nested.inner": "value"
        }
        assert result == expected

    def test_custom_separator(self):
        """Test flattening with a custom separator."""
        data = {"a": {"b": {"c": "value"}}}
        result = flatten_dict(data, sep="_")
        expected = {"a_b_c": "value"}
        assert result == expected

    def test_parent_key(self):
        """Test flattening with a parent key."""
        data = {"inner": {"value": 123}}
        result = flatten_dict(data, parent_key="outer")
        expected = {"outer.inner.value": 123}
        assert result == expected

    def test_parent_key_with_custom_separator(self):
        """Test flattening with parent key and custom separator."""
        data = {"inner": {"value": 123}}
        result = flatten_dict(data, parent_key="outer", sep="_")
        expected = {"outer_inner_value": 123}
        assert result == expected


class TestIsReservedName:
    """Tests for is_reserved_name function."""

    def test_reserved_names(self):
        """Test that known reserved names return True."""
        reserved_names = ["and", "or", "not", "in", "typeof", "is_valid"]
        for name in reserved_names:
            assert is_reserved_name(name) is True

    def test_reserved_names_case_insensitive(self):
        """Test that reserved names are case insensitive."""
        reserved_names = ["AND", "Or", "NoT", "IN", "TYPEOF", "IS_VALID"]
        for name in reserved_names:
            assert is_reserved_name(name) is True

    def test_mixed_case_reserved_names(self):
        """Test mixed case variations of reserved names."""
        assert is_reserved_name("And") is True
        assert is_reserved_name("OR") is True
        assert is_reserved_name("nOt") is True
        assert is_reserved_name("In") is True
        assert is_reserved_name("TypeOf") is True
        assert is_reserved_name("Is_Valid") is True

    def test_non_reserved_names(self):
        """Test that non-reserved names return False."""
        non_reserved = ["variable", "field", "data", "value", "custom", "user_name"]
        for name in non_reserved:
            assert is_reserved_name(name) is False

    def test_empty_string(self):
        """Test that empty string is not reserved."""
        assert is_reserved_name("") is False

    def test_similar_to_reserved(self):
        """Test names similar to but not exactly reserved names."""
        similar_names = ["andrew", "organize", "notice", "inside", "type", "valid"]
        for name in similar_names:
            assert is_reserved_name(name) is False

    def test_whitespace_names(self):
        """Test names with whitespace."""
        assert is_reserved_name(" and ") is False  # whitespace should make it not match
        assert is_reserved_name("and ") is False
        assert is_reserved_name(" and") is False