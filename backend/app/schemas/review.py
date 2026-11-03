from datetime import datetime

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
    created_at: datetime
    updated_at: datetime


class ReviewListOut(BaseModel):
    items: list[ReviewOut]
    count: int
    average: float
