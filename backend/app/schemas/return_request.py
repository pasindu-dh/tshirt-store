from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


ReturnReasonCode = Literal[
    "size_fit",
    "damaged",
    "wrong_item",
    "not_as_described",
    "changed_mind",
    "other",
]


class ReturnReasonOut(BaseModel):
    code: str
    label: str


class ReturnPolicyOut(BaseModel):
    window_days: int
    policy_text: str
    reasons: list[ReturnReasonOut]


class ReturnItemCreate(BaseModel):
    order_item_id: int = Field(gt=0)
    quantity: int = Field(ge=1)

    model_config = ConfigDict(extra="forbid")


class ReturnRequestCreate(BaseModel):
    items: list[ReturnItemCreate] = Field(
        min_length=1, max_length=50
    )
    reason_code: ReturnReasonCode = "other"
    reason: str = Field(min_length=3, max_length=500)
    notes: str = Field(default="", max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def unique_items(self):
        ids = [item.order_item_id for item in self.items]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "Each order item may appear only once in a return request."
            )

        return self


class ReturnReviewRequest(BaseModel):
    status: Literal["approved", "rejected", "completed"]
    note: str = Field(default="", max_length=500)

    model_config = ConfigDict(extra="forbid")


class ReturnLinkRefundRequest(BaseModel):
    refund_id: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class RefundSummaryOut(BaseModel):
    id: int
    amount: int
    kind: str
    status: str
    provider: str
    provider_refund_id: str
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReturnItemOut(BaseModel):
    id: int
    order_item_id: int | None
    variant_id: int | None
    quantity: int
    product_name: str
    size: str
    color: str
    sku: str
    restocked_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ReturnRequestOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    status: str
    reason_code: str
    reason: str
    notes: str
    refund_id: int | None
    refund: RefundSummaryOut | None
    review_note: str
    reviewed_at: datetime | None
    completed_at: datetime | None
    stock_restocked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[ReturnItemOut]

    model_config = ConfigDict(from_attributes=True)


class AdminReturnQueueOut(BaseModel):
    id: int
    order_id: int
    status: str
    reason_code: str
    reason: str
    created_at: datetime
    order_contact_name: str
    order_contact_email: str
    order_total: int
    item_count: int
    refund_id: int | None
    refund_status: str | None
