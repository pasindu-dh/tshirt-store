from pydantic import BaseModel


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
