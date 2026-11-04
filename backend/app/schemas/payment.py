from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PaymentConfigOut(BaseModel):
    provider: str
    online_enabled: bool
    currency: str
    mock_enabled: bool


class PaymentSessionOut(BaseModel):
    provider: str
    reference: str
    order_id: int
    amount: int
    currency: str
    action_url: str | None
    fields: dict[str, str]
    mock: bool


class PaymentStatusOut(BaseModel):
    order_id: int
    reference: str
    status: str


class PaymentEventOut(BaseModel):
    id: int
    status: str
    status_code: str
    provider_payment_id: str
    amount: int
    currency: str
    source: str
    note: str
    actor_user_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RefundOut(BaseModel):
    id: int
    order_id: int
    payment_id: int
    amount: int
    kind: str
    reason: str
    notes: str
    status: str
    provider: str
    provider_refund_id: str
    requested_by_user_id: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AdminRefundQueueOut(BaseModel):
    id: int
    order_id: int
    payment_id: int
    amount: int
    kind: str
    status: str
    provider: str
    provider_refund_id: str
    reason: str
    notes: str
    created_at: datetime
    completed_at: datetime | None
    order_contact_name: str
    order_contact_email: str
    order_total: int
    order_status: str
    order_payment_status: str
    payment_reference: str


class RefundCreate(BaseModel):
    kind: Literal["refund", "return"] = "refund"
    amount: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=300)
    notes: str = Field(default="", max_length=1000)
    process_with_provider: bool = False

    model_config = {"extra": "forbid"}


class RefundUpdate(BaseModel):
    status: Literal["pending", "processing", "refunded", "failed"]
    provider_refund_id: str = Field(default="", max_length=100)
    note: str = Field(default="", max_length=500)

    model_config = {"extra": "forbid"}


class AdminPaymentOut(BaseModel):
    id: int
    provider: str
    reference: str
    amount: int
    currency: str
    status: str
    provider_payment_id: str
    created_at: datetime
    updated_at: datetime
    paid_at: datetime | None
    events: list[PaymentEventOut]
    refunds: list[RefundOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ManualReconciliationRequest(BaseModel):
    status: Literal["paid", "failed", "cancelled", "chargedback"]
    provider_payment_id: str = Field(default="", max_length=100)
    note: str = Field(min_length=3, max_length=500)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def require_transaction_id(self):
        if self.status in {"paid", "chargedback"} and not (
            self.provider_payment_id.strip()
        ):
            raise ValueError(
                "A provider transaction ID is required for paid "
                "or chargedback reconciliation."
            )

        return self
