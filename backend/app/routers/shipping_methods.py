from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.shipping import ShippingMethodOut
from app.services import shipping

router = APIRouter(
    prefix="/shipping-methods",
    tags=["shipping"],
)


@router.get("", response_model=list[ShippingMethodOut])
def list_shipping_methods(
    db: Session = Depends(get_db),
):
    return shipping.list_methods(db, active_only=True)
