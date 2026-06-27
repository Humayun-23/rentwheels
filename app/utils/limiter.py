"""
Rate limiter instance for the application.
Import this module to access the limiter, avoiding circular imports.
"""
from slowapi import Limiter

# Initialize rate limiter

def get_client_ip(request):
    if request.client is None:
        return "unknown"
    return request.client.host

def get_limiter():
    return Limiter(key_func=get_client_ip, config_filename=None)

limiter = get_limiter() 
