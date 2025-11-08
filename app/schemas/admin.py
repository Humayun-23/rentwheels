from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class AdminCreate(BaseModel):
    admin_user_id: int
    email: str
    password: str

class AdminRead(BaseModel):
    admin_user_id: int
    email: str
    created_at: datetime

    class Config:
        orm_mode = True

class AdminUpdate(BaseModel):
    email: Optional[str]
    password: Optional[str]

class AdminOut(AdminRead):
    pass