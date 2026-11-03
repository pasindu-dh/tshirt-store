from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    contact_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=30)
    address_line1: str = Field(min_length=3, max_length=200)
    address_line2: str = Field(default="", max_length=200)
    city: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(default="", max_length=20)
    country: str = Field(default="Sri Lanka", min_length=2, max_length=100)
    notes: str = Field(default="", max_length=500)
    payment_method: Literal["cod"] = "cod"

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


class AdminOrderStatsOut(BaseModel):
    products_total: int
    products_active: int
    categories_total: int
    low_stock_variants: int
    orders_total: int
    pending_orders: int
    confirmed_orders: int
    shipped_orders: int
    delivered_orders: int
    cancelled_orders: int
    open_orders: int
    revenue: int

