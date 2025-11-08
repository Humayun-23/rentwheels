from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional


from app.utils.sanitization import sanitize_comment


class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)


class ReviewCreate(ReviewBase):
    @field_validator("comment", mode="before")
    @classmethod
    def sanitize_comment_field(cls, v):
        if v is not None:
            return sanitize_comment(v)
        return v


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)
    
    @field_validator("comment", mode="before")
    @classmethod
    def sanitize_comment_field(cls, v):
        if v is not None:
            return sanitize_comment(v)
        return v


class ReviewOut(ReviewBase):
    id: int
    customer_id: int
    shop_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)