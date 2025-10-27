from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from typing import Optional, Literal


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    phone_number: str = Field(..., min_length=10, max_length=20)  # Accept phone as string
    user_type: Literal["customer", "shop_owner"]


class User(UserCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    phone_number: Optional[str] = Field(None, min_length=10, max_length=20)
    
class UserOut(BaseModel):
    email: EmailStr
    phone_number: str
    user_type: Literal["customer", "shop_owner"]
    id: int
    created_at: datetime
    updated_at: datetime
    