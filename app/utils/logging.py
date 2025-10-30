import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
#from app.main import app


def configure_logging():
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer()
        ]
    )
    
def get_logger():
    return structlog.get_logger()

#middleware
