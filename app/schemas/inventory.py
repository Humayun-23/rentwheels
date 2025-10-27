from pydantic import BaseModel, ConfigDict
from datetime import datetime


class BikeInventoryCreate(BaseModel):
    bike_id: int
    shop_id: int
    total_quantity: int  # Total units of this bike
    # available_quantity and rented_quantity are auto-calculated


class BikeInventoryUpdate(BaseModel):
    total_quantity: int  # Can update total stock


class BikeInventory(BikeInventoryCreate):
    id: int
    available_quantity: int
    rented_quantity: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BikeInventoryOut(BikeInventory):
    """Schema for API responses showing inventory status"""
    
    @property
    def availability_percentage(self) -> float:
        """Calculate percentage of bikes available"""
        if self.total_quantity == 0:
            return 0.0
        return (self.available_quantity / self.total_quantity) * 100


class InventoryAvailability(BaseModel):
    """Simple schema to check if bikes are available for booking"""
    bike_id: int
    is_available: bool
    available_count: int
    total_count: int
