import pytest
from mcp_local_dev.utils.generic import dict_to_hash

def test_dict_to_hash():
    """Test dictionary hashing is consistent and order-independent"""
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 2, "a": 1}
    d3 = {"a": 1, "b": 3}
    
    # Same contents should hash the same regardless of order
    assert dict_to_hash(d1) == dict_to_hash(d2)
    
    # Different contents should hash differently
    assert dict_to_hash(d1) != dict_to_hash(d3)
    
    # Empty dict should have consistent hash
    assert dict_to_hash({}) == dict_to_hash({})
    
    # Nested structures should work
    nested1 = {"a": {"b": 1}}
    nested2 = {"a": {"b": 2}}
    assert dict_to_hash(nested1) != dict_to_hash(nested2)
