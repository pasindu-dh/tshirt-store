from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

StockMovementType = Literal[
    "initial_stock",
    "order_placed",
    "order_cancelled",
    "reservation_expired",
    "return_restocked",
    "manual_adjustment",
    "variant_removed",
    "product_deleted",
]


class StockMovementOut(BaseModel):
    id: int
    variant_id: int | None
    product_id: int | None
    order_id: int | None
    return_request_id: int | None
    actor_user_id: int | None
    movement_type: str
    quantity_delta: int
    stock_before: int
    stock_after: int
    product_name: str
    size: str
    color: str
    sku: str
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LowStockVariantOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_slug: str
    image: str
    size: str
    color: str
    sku: str
    stock: int
    low_stock_threshold: int


class StockAdjustmentRequest(BaseModel):
    quantity_delta: int = Field(ge=-100000, le=100000)
    reason: str = Field(min_length=3, max_length=300)

    model_config = ConfigDict(extra="forbid")

    @field_validator("quantity_delta")
    @classmethod
    def non_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError(
                "Adjustment quantity must not be zero."
            )

        return value

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError(
                "Adjustment reason must be at least 3 characters."
            )

        return value


class StockAdjustmentOut(BaseModel):
    variant: LowStockVariantOut
    movement: StockMovementOut
