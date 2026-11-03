from datetime import datetime, timezone
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

DiscountType = Literal["percent", "fixed"]


class CouponCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    description: str = Field(default="", max_length=200)
    discount_type: DiscountType = "percent"
    value: int = Field(ge=1)
    min_subtotal: int = Field(default=0, ge=0)
    usage_limit: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("Coupon code cannot be blank")

        return normalized

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_coupon(self):
        if self.discount_type == "percent" and self.value > 100:
            raise ValueError("Percentage discounts cannot exceed 100")

        if (
            self.starts_at is not None
            and self.expires_at is not None
            and _as_utc(self.expires_at) <= _as_utc(self.starts_at)
        ):
            raise ValueError("Expiry must be after the start date")

        return self


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


class CouponUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=40)
    description: str | None = Field(default=None, max_length=200)
    discount_type: DiscountType | None = None
    value: int | None = Field(default=None, ge=1)
    min_subtotal: int | None = Field(default=None, ge=0)
    usage_limit: int | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("Coupon code cannot be blank")

        return normalized

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CouponOut(BaseModel):
    id: int
    code: str
    description: str
    discount_type: str
    value: int
    min_subtotal: int
    usage_limit: int | None
    used_count: int
    starts_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CouponPreviewRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)

    model_config = ConfigDict(extra="forbid")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("Coupon code cannot be blank")

        return normalized


class CouponPreviewOut(BaseModel):
    code: str
    description: str
    discount_type: str
    value: int
    discount_amount: int
    subtotal: int
    shipping_fee: int
    total: int
