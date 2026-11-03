from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.order import OrderCreate, OrderOut
from app.services import orders as order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return order_service.create_order(db, current_user, payload)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=list[OrderOut])
def list_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return order_service.get_orders(db, current_user.id)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = order_service.get_order(db, current_user.id, order_id)

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order
