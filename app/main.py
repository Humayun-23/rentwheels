from fastapi.middleware.gzip import GZipMiddleware
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import PlainTextResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

from app.utils.limiter import limiter
from app.utils.logging_config import configure_logging, LoggingMiddleware
from app.api.v1 import auth, reviews, users, shops, booking, listing, searchvehicle, passwordreset, payments
from app.api.v1 import inventory
from app.config import settings
from app.db.database import get_db, SessionLocal

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


app = FastAPI(
    title="RentWheels API",
    description="Bike rental platform API",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Add logging middleware FIRST (before other middleware)
app.add_middleware(LoggingMiddleware)

# Add trusted host middleware for Azure (set X-Forwarded-Proto, etc.)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Allow all hosts since we're behind Azure's load balancer
)

# Set limiter on app state and register exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware with proper security settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_origin_regex=r"https://(ride-elegance-[a-zA-Z0-9-]+-.*\.vercel\.app|ride-elegance\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ✅ FIXED: Explicit methods
    allow_headers=["Content-Type", "Authorization"],  # ✅ FIXED: Explicit headers
    expose_headers=["Content-Length", "X-Total-Count"],
    max_age=600,  # Cache preflight requests for 10 minutes
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(shops.router, prefix="/api/v1")
app.include_router(booking.router, prefix="/api/v1")
app.include_router(listing.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(searchvehicle.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(passwordreset.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Welcome to RentWheels API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api")
def api_info():
    """Backend metadata endpoint for clients and health tooling."""
    return {
        "message": "Welcome to RentWheels API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    # Disallow all bots on the API domain
    content = "User-agent: *\nDisallow: /"
    return PlainTextResponse(content=content)

@app.on_event("startup")
async def startup_event():
    """Verify database connection on startup (optional for development)"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection verified at startup")
    except Exception as e:
        logger.error(f"❌ Failed to connect to database at startup: {str(e)}")
        # Log warning but don't fail - DB will be checked on first API call
        logger.warning(f"⚠️ Database unavailable at startup. Connection will be retried on first request. Error: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🔴 Application shutting down")
    from app.db.database import dispose_engine
    dispose_engine()


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Liveness probe - application is running"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/ready")
def readiness_probe(db: Session = Depends(get_db)):
    """Readiness probe - application is ready to serve requests"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Not ready")
