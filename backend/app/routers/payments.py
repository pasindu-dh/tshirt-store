from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.payment import (
    PaymentConfigOut,
    PaymentSessionOut,
    PaymentStatusOut,
)
from app.services import payments as payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/config", response_model=PaymentConfigOut)
def payment_config():
    return payment_service.get_config()


@router.post(
    "/orders/{order_id}/session",
    response_model=PaymentSessionOut,
)
def create_payment_session(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.create_session(db, current_user, order_id)


@router.post(
    "/orders/{order_id}/mock-complete",
    response_model=PaymentStatusOut,
)
def complete_mock_payment(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return payment_service.complete_mock_payment(
        db, current_user, order_id
    )


@router.post("/payhere/notify")
async def payhere_notify(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    payload = {key: str(value) for key, value in form.items()}
    return payment_service.process_payhere_notification(db, payload)
