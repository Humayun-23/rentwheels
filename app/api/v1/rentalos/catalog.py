from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status, Response
from sqlalchemy.orm import Session
from app.api.v1.oauth2 import get_current_user
from app.db.database import get_db
from app.db.models import *
from app.schemas.rentalos import *
from .utils import *

router = APIRouter()

@router.get("/catalog/vehicles", response_model=list[CatalogVehicleResponse])
def get_catalog_vehicles(
    response: Response,
    shop_id: int = Query(...),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List RentalOS catalog vehicles for a shop."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    assert_rentalos_shop_access(db, shop_id, current_user)
    if (start_time and not end_time) or (end_time and not start_time):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both start_time and end_time are required for availability checks.",
        )
    if start_time and end_time:
        start_time, end_time = _validate_time_range(start_time, end_time)

    bikes = (
        db.query(Bike)
        .options(joinedload(Bike.image))
        .filter(Bike.shop_id == shop_id)
        .all()
    )
    availability_statuses = _catalog_availability_statuses(db, bikes, start_time, end_time)

    return [
        CatalogVehicleResponse(
            bike_id=bike.id,
            shop_id=bike.shop_id,
            name=bike.name,
            model=bike.model,
            bike_type=bike.bike_type,
            price_per_hour=bike.price_per_hour,
            price_per_day=bike.price_per_day,
            condition=bike.condition,
            maintenance_status=bike.maintenance_status,
            is_available=bike.is_available,
            image_url=_bike_image_url(bike),
            rentalos_availability_status=availability_statuses[bike.id],
        )
        for bike in bikes
    ]


