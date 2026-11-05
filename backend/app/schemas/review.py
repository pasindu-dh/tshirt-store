from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = Field(default="", max_length=120)
    comment: str = Field(default="", max_length=2000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", "comment")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ReviewOut(BaseModel):
    id: int
    product_id: int
    user_id: int
    user_name: str
    rating: int
    title: str
    comment: str
    status: str = "published"
    created_at: datetime
    updated_at: datetime


class ReviewListOut(BaseModel):
    items: list[ReviewOut]
    count: int
    average: float
    my_review: ReviewOut | None = None


class AdminReviewOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_slug: str
    user_id: int
    user_name: str
    user_email: str
    rating: int
    title: str
    comment: str
    status: str
    created_at: datetime
    updated_at: datetime


class AdminReviewStatusUpdate(BaseModel):
    status: Literal["pending", "published", "rejected"]

    model_config = ConfigDict(extra="forbid")
