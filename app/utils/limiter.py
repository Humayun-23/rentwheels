import os
from slowapi import Limiter

def get_client_ip(request):
    if request.client is None:
        return "unknown"
    return request.client.host

def get_limiter():
    # Clean workaround: Use /dev/null if .env doesn't exist to prevent crashes
    config_file = ".env" if os.path.exists(".env") else os.devnull
    return Limiter(key_func=get_client_ip, config_filename=config_file)

limiter = get_limiter()
