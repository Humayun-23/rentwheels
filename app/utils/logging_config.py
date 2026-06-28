import structlog
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import sys
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()

        try:
            if message.startswith("{") and message.endswith("}"):
                parsed = json.loads(message)
                if isinstance(parsed, dict):
                    return message
        except (ValueError, TypeError):
            pass

        log_obj = {
            "level": record.levelname,
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "message": message,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


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
    
    root_logger = logging.getLogger()
    root_logger.handlers = [
        handler
        for handler in root_logger.handlers
        if not isinstance(handler.formatter, JSONFormatter)
    ]
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


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
