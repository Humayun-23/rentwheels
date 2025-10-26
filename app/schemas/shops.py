from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime, time
from typing import Optional
from pydantic.types import conint

class ShopCreate(BaseModel):
    name: str
    description: Optional[str] = None
    owner_id: int 
    phone_number: conint(gt=0)
    address: str
    city: str
    state: Optional[str] = None
    zip_code: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    is_active: bool = True


class Shop(ShopCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ShopUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    phone_number: Optional[conint(gt=0)] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    is_active: Optional[bool] = None


class ShopOut(Shop):
    pass