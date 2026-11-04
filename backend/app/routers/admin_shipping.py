from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.schemas.shipping import (
    ShippingMethodCreate,
    ShippingMethodOut,
    ShippingMethodUpdate,
)
from app.services import shipping

router = APIRouter(
    prefix="/admin/shipping-methods",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[ShippingMethodOut])
def list_shipping_methods(
    db: Session = Depends(get_db),
):
    return shipping.list_methods(db)


@router.post(
    "",
    response_model=ShippingMethodOut,
    status_code=status.HTTP_201_CREATED,
)
def create_shipping_method(
    payload: ShippingMethodCreate,
    db: Session = Depends(get_db),
):
    try:
        return shipping.create_method(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shipping method with that name already exists.",
        ) from exc


@router.patch(
    "/{method_id}",
    response_model=ShippingMethodOut,
)
def update_shipping_method(
    method_id: int,
    payload: ShippingMethodUpdate,
    db: Session = Depends(get_db),
):
    method = shipping.get_method(db, method_id)

    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping method not found.",
        )

    try:
        return shipping.update_method(
            db, method, payload
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shipping method with that name already exists.",
        ) from exc


@router.delete(
    "/{method_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_shipping_method(
    method_id: int,
    db: Session = Depends(get_db),
):
    method = shipping.get_method(db, method_id)

    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping method not found.",
        )

    shipping.delete_method(db, method)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
