from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, reviews, users, shops, booking, listing, searchvehicle
from app.api.v1 import inventory


app = FastAPI(
    title="RentWheels API",
    description="Bike rental platform API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to specific origins in production
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


@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "Welcome to RentWheels API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
