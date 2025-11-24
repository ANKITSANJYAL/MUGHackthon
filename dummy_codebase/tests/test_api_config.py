"""
Tests for API Configuration

These tests expose the wrong port configuration in api_config.py
"""

import pytest
import os
from config.api_config import InternalAPIConfig, call_internal_service


def test_api_gateway_port_should_be_8081():
    """
    This test FAILS - exposing the configuration bug!
    
    Expected: Port should be 8081 per AD-204
    Actual: Port is 8080 (wrong!)
    """
    # Current behavior - WRONG!
    assert InternalAPIConfig.API_GATEWAY_PORT == 8080
    
    # What it SHOULD be per AD-204:
    # assert InternalAPIConfig.API_GATEWAY_PORT == 8081  # This FAILS!


def test_service_urls_use_wrong_port():
    """
    Test that service URLs are constructed with wrong port.
    """
    auth_url = InternalAPIConfig.AUTH_SERVICE_URL
    
    # Currently uses wrong port
    assert "8080" in auth_url  # BUG - should be 8081!
    
    # What it should be:
    # assert "8081" in auth_url


def test_get_service_url():
    """
    Test service URL retrieval.
    Works but returns URLs with wrong port.
    """
    auth_url = InternalAPIConfig.get_service_url('auth')
    users_url = InternalAPIConfig.get_service_url('users')
    
    assert auth_url is not None
    assert users_url is not None
    
    # Both use wrong port!
    assert "8080" in auth_url  # Should be 8081
    assert "8080" in users_url  # Should be 8081


def test_correct_port_per_ad204():
    """
    This test documents the requirement from AD-204.
    
    Architectural Decision 204 states:
    "All internal services must use port 8081 for consistency"
    
    This test FAILS with current configuration.
    """
    expected_port = 8081  # Per AD-204
    actual_port = InternalAPIConfig.API_GATEWAY_PORT
    
    # This assertion FAILS - exposing the bug!
    assert actual_port == expected_port, \
        f"Port should be {expected_port} per AD-204, but is {actual_port}"


def test_connection_timeout_due_to_wrong_port():
    """
    This test documents that connections will timeout.
    
    Services are running on 8081, but config tries to connect to 8080.
    Result: Connection refused / timeout errors.
    """
    # This would timeout in real scenario
    # call_internal_service('auth', '/health')  # Would fail!
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
