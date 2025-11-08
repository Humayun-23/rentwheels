"""
Rate limiter instance for the application.
Import this module to access the limiter, avoiding circular imports.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter

def get_limiter():
    return Limiter(key_func=get_remote_address)

limiter = get_limiter() 
