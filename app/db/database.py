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

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "300")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    connect_args={
        "connect_timeout": 10,
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
