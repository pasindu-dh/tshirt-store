from datetime import datetime

from pydantic import BaseModel

from app.schemas.order import OrderOut
from app.schemas.return_request import ReturnRequestOut


class AdminCustomerOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime
    order_count: int
    delivered_orders: int
    cancelled_orders: int
    gross_spend: int
    refunded_total: int
    pending_refund_total: int
    net_spend: int
    returns_count: int
    open_returns: int
    last_order_at: datetime | None


class AdminCustomerDetailOut(AdminCustomerOut):
    orders: list[OrderOut]
    returns: list[ReturnRequestOut]
