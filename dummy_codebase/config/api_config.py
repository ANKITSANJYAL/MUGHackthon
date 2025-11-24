"""
Internal API Gateway Configuration

Handles routing and configuration for internal service-to-service communication.
"""

import os


class InternalAPIConfig:
    """Configuration for internal API services."""
    
    # BUG: Using default port 8080 instead of company standard 8081
    # This violates AD-204 architectural decision
    API_GATEWAY_HOST = os.getenv('API_HOST', 'localhost')
    API_GATEWAY_PORT = int(os.getenv('API_PORT', 8080))  # WRONG! Should be 8081
    
    # Authentication service endpoints
    AUTH_SERVICE_URL = f"http://{API_GATEWAY_HOST}:{API_GATEWAY_PORT}/auth"
    
    # User service endpoints  
    USER_SERVICE_URL = f"http://{API_GATEWAY_HOST}:{API_GATEWAY_PORT}/users"
    
    # Activity service endpoints
    ACTIVITY_SERVICE_URL = f"http://{API_GATEWAY_HOST}:{API_GATEWAY_PORT}/activity"
    
    @classmethod
    def get_service_url(cls, service_name: str) -> str:
        """
        Get the full URL for an internal service.
        
        Args:
            service_name: Name of the service (auth, users, activity)
            
        Returns:
            Full service URL
        """
        service_map = {
            'auth': cls.AUTH_SERVICE_URL,
            'users': cls.USER_SERVICE_URL,
            'activity': cls.ACTIVITY_SERVICE_URL
        }
        return service_map.get(service_name, '')


def call_internal_service(service_name: str, endpoint: str, method: str = 'GET', data: dict = None):
    """
    Makes a call to an internal service.
    
    BUG: Will timeout due to wrong port configuration!
    
    Args:
        service_name: Service to call
        endpoint: API endpoint path
        method: HTTP method
        data: Request payload
        
    Returns:
        Response data
    """
    import requests
    
    base_url = InternalAPIConfig.get_service_url(service_name)
    full_url = f"{base_url}{endpoint}"
    
    # This will fail because port 8080 is blocked by legacy firewall
    # Company standard requires port 8081 per AD-204
    response = requests.request(method, full_url, json=data, timeout=5)
    return response.json()
