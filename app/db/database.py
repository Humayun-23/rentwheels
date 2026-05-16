import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from starlette.responses import Response
from app.config import settings

# Database URL - PostgreSQL
# Set DATABASE_URL environment variable or it will use default
# Example: postgresql://username:password@localhost:5432/rentwheels
# Add sslmode=require for cloud databases like Neon
DATABASE_URL = f"postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}?sslmode=require"

# Connection pool configuration optimized for Azure PostgreSQL
# Adjust pool_size based on your Azure tier:
# - Burstable B1ms: pool_size=3-5, max_overflow=2
# - General Purpose D2s: pool_size=10-15, max_overflow=5
# - Memory Optimized E2s: pool_size=20+, max_overflow=10

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))  # ✅ FIXED: Reduced for Azure
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "3"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "600"))  # ✅ FIXED: 10 min for Azure timeout
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # Wait up to 30s for connection

engine = create_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=POOL_RECYCLE,  # Recycle connections to handle idle timeouts
    pool_timeout=POOL_TIMEOUT,  # Timeout for getting connection from pool
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",  # Debug logging
    connect_args={
        "connect_timeout": 10,  # 10 second connection timeout
    } if "sqlite" not in DATABASE_URL else {"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def dispose_engine():
    """Properly cleanup connection pool on shutdown"""
    engine.dispose()


def set_cache_headers(response: Response, max_age: int = 300, public: bool = True):
    """Helper to set HTTP cache control headers for responses"""
    cache_control = f"public, max-age={max_age}" if public else f"private, max-age={max_age}"
    response.headers["Cache-Control"] = cache_control
    response.headers["Vary"] = "Accept-Encoding"
    return response
