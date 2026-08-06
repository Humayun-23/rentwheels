import os
from slowapi import Limiter

# Workaround for slowapi crashing when .env doesn't exist (e.g. on Heroku)
if not os.path.exists(".env"):
    open(".env", "w").close()

def get_client_ip(request):
    if request.client is None:
        return "unknown"
    return request.client.host

def get_limiter():
    return Limiter(key_func=get_client_ip)

limiter = get_limiter()
