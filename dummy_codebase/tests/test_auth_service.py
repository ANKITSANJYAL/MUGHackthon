"""
Tests for Authentication Service

These tests expose the bugs in auth_service.py
"""

import pytest
from services.auth_service import _security_hash_id, validate_user_session


def test_security_hash_id_without_org():
    """
    This test PASSES with current buggy code but shouldn't!
    The function is missing org prefix.
    """
    token = "test-token-123"
    result = _security_hash_id(token)
    assert len(result) == 16  # Current behavior - wrong!


def test_security_hash_id_should_include_org_prefix():
    """
    This test FAILS - exposing the bug!
    
    Expected: Hash should include organization context
    Actual: Missing org prefix as per AD-305
    """
    token = "test-token-123"
    org_id = "ORG-ABC"
    
    # This should fail because current implementation doesn't support org_id
    with pytest.raises(TypeError):
        result = _security_hash_id(token, org_id)  # Function doesn't accept org_id!


def test_validate_user_session():
    """
    Test session validation.
    Works but uses buggy hash function internally.
    """
    token = "valid-session-token"
    result = validate_user_session(token)
    
    assert result['authenticated'] is True
    assert 'user_id' in result


def test_multi_tenant_token_hashing():
    """
    This test FAILS - exposing multi-tenant bug!
    
    Two users from different orgs with same token should have different hashes.
    """
    token = "same-token"
    
    # Currently both return same hash (BUG!)
    hash1 = _security_hash_id(token)
    hash2 = _security_hash_id(token)
    
    assert hash1 == hash2  # This passes but shouldn't be the same for diff orgs!
    
    # What SHOULD happen (will fail with current code):
    # hash1 = _security_hash_id(token, "ORG-1")
    # hash2 = _security_hash_id(token, "ORG-2")
    # assert hash1 != hash2  # Different orgs should have different hashes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
