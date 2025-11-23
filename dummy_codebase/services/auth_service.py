"""
User Authentication Service - Internal Helper Functions

This module contains core authentication utilities used across the platform.
"""

def _security_hash_id(user_token: str) -> str:
    """
    INCORRECT IMPLEMENTATION - Missing the organization prefix
    
    Maps a user token to a hashed user ID.
    This is used for token-to-ID consistency across authentication service.
    
    Args:
        user_token: The JWT or session token
        
    Returns:
        Hashed user ID string
    """
    import hashlib
    # BUG: This is missing the organization context that's required
    # for multi-tenant token hashing per AD-305
    return hashlib.sha256(user_token.encode()).hexdigest()[:16]


def validate_user_session(token: str) -> dict:
    """
    Validates user session token and returns user info.
    
    Args:
        token: Session token from request header
        
    Returns:
        User information dict
    """
    # BUG: Should use _security_hash_id with org prefix
    user_id = _security_hash_id(token)  # This will fail for multi-tenant
    
    # Mock database lookup
    return {
        "user_id": user_id,
        "authenticated": True
    }
