from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Literal

from app.db.database import get_db
from app.db.models import Bike
from app.schemas.bikes import BikeOut

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/vehicles", response_model=List[BikeOut])
def search_vehicles(
    vehicle_type: Optional[Literal["scooty", "bike", "car"]] = Query(None, description="Type of vehicle to search for"),
    engine_cc: Optional[int] = Query(None, description="Engine CC (e.g., 150, 250, 500)"),
    cc_min: Optional[int] = Query(None, description="Minimum engine CC"),
    cc_max: Optional[int] = Query(None, description="Maximum engine CC"),
    is_available: Optional[bool] = Query(None, description="Only available vehicles"),
    shop_id: Optional[int] = Query(None, description="Filter by shop ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Search for vehicles by type and engine CC with pagination.
    
    Query Parameters:
    - vehicle_type: Filter by "scooty", "bike", or "car"
    - engine_cc: Search for exact engine CC
    - cc_min: Minimum engine CC (for range search)
    - cc_max: Maximum engine CC (for range search)
    - is_available: Filter only available vehicles
    - shop_id: Filter by shop ID
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return (pagination, max 100)
    
    Examples:
    - GET /api/v1/search/vehicles?vehicle_type=bike
    - GET /api/v1/search/vehicles?vehicle_type=scooty&engine_cc=150
    - GET /api/v1/search/vehicles?vehicle_type=car&cc_min=1000&cc_max=2000
    - GET /api/v1/search/vehicles?engine_cc=500&is_available=true&skip=0&limit=20
    """
    query = db.query(Bike)
    
    # Filter by vehicle type
    if vehicle_type:
        query = query.filter(Bike.bike_type == vehicle_type)
    
    # Filter by exact engine CC
    if engine_cc is not None:
        query = query.filter(Bike.engine_cc == engine_cc)
    
    # Filter by CC range
    if cc_min is not None:
        query = query.filter(Bike.engine_cc >= cc_min)
    if cc_max is not None:
        query = query.filter(Bike.engine_cc <= cc_max)
    
    # Filter by availability
    if is_available is not None:
        query = query.filter(Bike.is_available == is_available)
    
    # Filter by shop
    if shop_id is not None:
        query = query.filter(Bike.shop_id == shop_id)
    
    vehicles = query.offset(skip).limit(limit).all()
    return vehicles


@router.get("/vehicles/type/{vehicle_type}", response_model=List[BikeOut])
def search_vehicles_by_type(
    vehicle_type: Literal["scooty", "bike", "car"],
    is_available: Optional[bool] = Query(None, description="Only available vehicles"),
    shop_id: Optional[int] = Query(None, description="Filter by shop ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Search vehicles by type only with pagination (simplified endpoint).
    
    Path Parameters:
    - vehicle_type: "scooty", "bike", or "car"
    
    Query Parameters:
    - is_available: Filter only available vehicles (optional)
    - shop_id: Filter by shop ID (optional)
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return (pagination, max 100)
    
    Examples:
    - GET /api/v1/search/vehicles/type/bike
    - GET /api/v1/search/vehicles/type/scooty?is_available=true
    - GET /api/v1/search/vehicles/type/car?shop_id=1&skip=0&limit=20
    """
    query = db.query(Bike).filter(Bike.bike_type == vehicle_type)
    
    if is_available is not None:
        query = query.filter(Bike.is_available == is_available)
    
    if shop_id is not None:
        query = query.filter(Bike.shop_id == shop_id)
    
    vehicles = query.offset(skip).limit(limit).all()
    return vehicles