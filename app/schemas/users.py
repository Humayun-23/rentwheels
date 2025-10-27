from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, Literal
from pydantic.types import conint

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    phone_number: conint(gt=0)
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
    phone_number: Optional[conint(gt=0)] = None
    
class UserOut(User):
    pass