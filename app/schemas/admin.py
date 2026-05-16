from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class AdminCreate(BaseModel):
    email: str  # ✅ FIXED: Removed non-existent admin_user_id field
    password: str

class AdminRead(BaseModel):
    id: int  # ✅ FIXED: Changed from admin_user_id to id
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)  # ✅ FIXED: Updated from orm_mode to v2 syntax

class AdminUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

class AdminOut(AdminRead):
    pass