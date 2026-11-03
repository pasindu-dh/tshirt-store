from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.wishlist import WishlistItemOut
from app.services import wishlist as wishlist_service

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("", response_model=list[WishlistItemOut])
def list_wishlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return wishlist_service.list_items(db, current_user.id)


@router.put("/items/{product_id}", response_model=WishlistItemOut)
def add_wishlist_item(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return wishlist_service.add_item(db, current_user.id, product_id)


@router.delete(
    "/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_wishlist_item(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wishlist_service.remove_item(db, current_user.id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
