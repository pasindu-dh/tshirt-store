from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReturnRequestCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    notes: str = Field(default="", max_length=1000)

    model_config = ConfigDict(extra="forbid")


class ReturnReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]
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


class ReturnRequestOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    status: str
    reason: str
    notes: str
    refund_id: int | None
    refund: RefundSummaryOut | None
    review_note: str
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
