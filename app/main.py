from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from app.utils.limiter import limiter
from app.api.v1 import auth, reviews, users, shops, booking, listing, searchvehicle, passwordreset
from app.api.v1 import inventory
from app.config import settings
from app.db.database import get_db


app = FastAPI(
    title="RentWheels API",
    description="Bike rental platform API",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,

)

# Set limiter on app state and register exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Welcome to RentWheels API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database unavailable")
