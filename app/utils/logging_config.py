import structlog
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import sys
import json


def configure_logging():
    """Configure structlog for JSON logging (suitable for Azure Application Insights)"""
    # Configure structlog with stdlib logger factory
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure Python's standard logging with JSON output
    handler = logging.StreamHandler(sys.stdout)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Simple JSON formatter for stdlib logging
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                "level": record.levelname,
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_obj["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_obj)
    
    handler.setFormatter(JSONFormatter())


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP (handles reverse proxy like Azure)
        x_forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        start_time = time.time()
        
        # Create logger with context
        logger = structlog.get_logger().bind(
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
        )
        
        logger.info("request_started")
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            logger.bind(
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            ).info("request_completed")
            
            return response
            
        except Exception as exc:
            duration = time.time() - start_time
            logger.bind(
                error=str(exc),
                duration_ms=round(duration * 1000, 2),
            ).error("request_failed")
            raise


def get_logger():
    """Get a structured logger instance"""
    return structlog.get_logger()
