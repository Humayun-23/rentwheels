from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)


class ReviewOut(ReviewBase):
    id: int
    customer_id: int
    shop_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)