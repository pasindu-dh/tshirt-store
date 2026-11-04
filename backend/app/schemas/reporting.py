from datetime import date
from typing import Literal

from pydantic import BaseModel


class FinancialSummaryOut(BaseModel):
    gross_revenue: int
    refunded_total: int
    pending_refund_total: int
    net_revenue: int
    delivered_orders: int
    refund_count: int
    refunded_count: int
    returns_total: int
    open_returns: int
    completed_returns: int
    returned_units: int


class FinancialPeriodOut(BaseModel):
    period: str
    delivered_orders: int
    gross_revenue: int
    refunded_total: int
    net_revenue: int


class RefundStatusBreakdownOut(BaseModel):
    status: str
    count: int
    amount: int


class ReturnStatusBreakdownOut(BaseModel):
    status: str
    count: int


class FinancialReportOut(BaseModel):
    date_from: date | None
    date_to: date | None
    group_by: Literal["day", "month"]
    summary: FinancialSummaryOut
    periods: list[FinancialPeriodOut]
    refund_statuses: list[RefundStatusBreakdownOut]
    return_statuses: list[ReturnStatusBreakdownOut]
