import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Booking, Bike, Shop
from app.schemas.statistics import (
    VehicleStatsResponse, 
    ShopStatsResponse, 
    BookingStatsResponse,
    StatsSummaryResponse
)


router = APIRouter(prefix="/statistics", tags=["statistics"])

# In-memory cache for summary stats
STATS_CACHE = {
    "summary": None,
    "expires_at": 0
}
TTL_SECONDS = 48 * 60 * 60  # 48 hours


@router.get("/summary", response_model=StatsSummaryResponse)
def get_stats_summary(
    db: Session = Depends(get_db),
):
    now = time.time()
    
    # Return cached data if valid
    if STATS_CACHE["summary"] and now < STATS_CACHE["expires_at"]:
        return STATS_CACHE["summary"]

    # Calculate new stats
    total_shops = db.query(Shop).count()
    total_vehicles = db.query(Bike).count()
    total_bookings = db.query(Booking).count()
    
    summary = {
        "total_shops": total_shops,
        "total_vehicles": total_vehicles,
        "total_bookings": total_bookings
    }
    
    # Update cache
    STATS_CACHE["summary"] = summary
    STATS_CACHE["expires_at"] = now + TTL_SECONDS
    
    return summary


@router.get("/shops", response_model=ShopStatsResponse)
def total_shops(
    db: Session = Depends(get_db),
):
    total_shops = db.query(Shop).count()
    return {"total_shops": total_shops}


@router.get("/vehicles", response_model=VehicleStatsResponse)
def total_vehicles(
    db: Session = Depends(get_db),
):
    total_vehicles = db.query(Bike).count()
    return {"total_vehicles": total_vehicles}


@router.get("/bookings", response_model=BookingStatsResponse)
def total_bookings(
    db: Session = Depends(get_db),
):
    total_bookings = db.query(Booking).count()
    return {"total_bookings": total_bookings}
