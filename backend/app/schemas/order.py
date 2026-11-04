from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


class OrderCreate(BaseModel):
    contact_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=30)
    address_line1: str = Field(min_length=3, max_length=200)
    address_line2: str = Field(default="", max_length=200)
    city: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(default="", max_length=20)
    country: str = Field(default="Sri Lanka", min_length=2, max_length=100)
    notes: str = Field(default="", max_length=500)
    payment_method: Literal["cod", "online"] = "cod"
    coupon_code: str = Field(default="", max_length=40)

    model_config = ConfigDict(extra="forbid")


class OrderItemOut(BaseModel):
    id: int
    product_id: int | None
    variant_id: int | None
    product_name: str
    product_slug: str
    image: str
    size: str
    color: str
    sku: str
    unit_price: int
    quantity: int
    line_total: int

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    status: str
    payment_method: str
    payment_status: str
    subtotal: int
    shipping_fee: int
    discount_code: str
    discount_amount: int
    total: int
    contact_name: str
    contact_email: str
    phone: str
    address_line1: str
    address_line2: str
    city: str
    postal_code: str
    country: str
    notes: str
    created_at: datetime
    reservation_expires_at: datetime | None = None
    delivered_at: datetime | None = None
    stock_released_at: datetime | None = None
    stock_release_reason: str = ""
    items: list[OrderItemOut]

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: Literal[
        "pending",
        "confirmed",
        "shipped",
        "delivered",
        "cancelled",
    ]

    model_config = ConfigDict(extra="forbid")


class OrderDetailsUpdate(BaseModel):
    contact_name: str | None = Field(
        default=None, min_length=2, max_length=120
    )
    contact_email: EmailStr | None = None
    phone: str | None = Field(
        default=None, min_length=5, max_length=30
    )
    address_line1: str | None = Field(
        default=None, min_length=3, max_length=200
    )
    address_line2: str | None = Field(
        default=None, max_length=200
    )
    city: str | None = Field(
        default=None, min_length=2, max_length=100
    )
    postal_code: str | None = Field(
        default=None, max_length=20
    )
    country: str | None = Field(
        default=None, min_length=2, max_length=100
    )
    notes: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "contact_name",
        "phone",
        "address_line1",
        "city",
        "country",
    )
    @classmethod
    def strip_required(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        if value is None:
            return value

        stripped = value.strip()
        minimums = {
            "contact_name": 2,
            "phone": 5,
            "address_line1": 3,
            "city": 2,
            "country": 2,
        }

        if len(stripped) < minimums[info.field_name]:
            raise ValueError(
                f"{info.field_name} cannot be blank or too short"
            )

        return stripped

    @field_validator("address_line2", "postal_code", "notes")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one field to update"
            )

        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self


class OrderAuditEventOut(BaseModel):
    id: int
    order_id: int
    actor_user_id: int | None
    action: str
    changes: dict
    created_at: datetime


class AdminOrderStatsOut(BaseModel):
    products_total: int
    products_active: int
    categories_total: int
    low_stock_variants: int
    out_of_stock_variants: int
    orders_total: int
    pending_orders: int
    confirmed_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int
    open_orders: int
    revenue: int
    gross_revenue: int
    refunded_total: int
    pending_refund_total: int
    refund_count: int
    open_returns: int
    returns_total: int

