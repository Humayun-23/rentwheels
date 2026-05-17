from pydantic import BaseModel, EmailStr, ConfigDict, Field, computed_field
from datetime import datetime, time
from typing import Optional


class ShopCreate(BaseModel):
    name: str
    description: Optional[str] = None
    phone_number: str = Field(..., min_length=10, max_length=20)
    address: str
    city: str
    state: Optional[str] = None
    zip_code: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    is_active: bool = True
    # Note: owner_id is automatically set from the authenticated user in the endpoint


class Shop(ShopCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ShopUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    is_active: Optional[bool] = None

class ShopImage(BaseModel):
    id: int
    image_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ShopOut(Shop):
    image: list[ShopImage] = []

    @computed_field
    @property
    def image_url(self) -> str | None:
        if self.image:
            return self.image[0].image_url
        return None