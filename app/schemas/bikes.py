from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Literal


class BikeCreate(BaseModel):
    shop_id: int  # Required: which shop owns this bike
    name: str
    model: str
    bike_type: Literal["scooty", "bike", "car", "mountain", "road", "hybrid", "electric"]
    engine_cc: Optional[int] = None  # Engine displacement in CC
    description: Optional[str] = None
    price_per_hour: int  # Price in cents (e.g., 500 = $5.00)
    price_per_day: int   # Price in cents (e.g., 2500 = $25.00)
    condition: Literal["excellent", "good", "fair"] = "good"
    is_available: bool = True


class Bike(BikeCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BikeUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    bike_type: Optional[Literal["scooty", "bike", "car", "mountain", "road", "hybrid", "electric"]] = None
    engine_cc: Optional[int] = None  # Engine displacement in CC
    description: Optional[str] = None
    price_per_hour: Optional[int] = None
    price_per_day: Optional[int] = None
    condition: Optional[Literal["excellent", "good", "fair"]] = None
    is_available: Optional[bool] = None


class BikeOut(Bike):
    pass

