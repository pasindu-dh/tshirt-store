from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.cart import (
    CartItemAdd,
    CartItemUpdate,
    CartMergeRequest,
    CartOut,
)
from app.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cart_service.get_cart(db, current_user.id)


@router.post("/items", response_model=CartOut)
def add_cart_item(
    payload: CartItemAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cart_service.add_item(
        db, current_user.id, payload.variant_id, payload.quantity
    )


@router.put("/items/{item_id}", response_model=CartOut)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cart_service.update_item(
        db, current_user.id, item_id, payload.quantity
    )


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cart_service.remove_item(db, current_user.id, item_id)


@router.delete("", response_model=CartOut)
def clear_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cart_service.clear_cart(db, current_user.id)


@router.post("/merge", response_model=CartOut)
def merge_cart(
    payload: CartMergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return cart_service.merge_cart(db, current_user.id, payload)
