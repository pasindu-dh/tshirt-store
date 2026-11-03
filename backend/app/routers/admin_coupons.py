from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.schemas.coupon import CouponCreate, CouponOut, CouponUpdate
from app.services import coupons as coupon_service

router = APIRouter(
    prefix="/admin/coupons",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _require_coupon(coupon_id: int, db: Session):
    coupon = coupon_service.get_coupon(db, coupon_id)

    if coupon is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coupon not found",
        )

    return coupon


@router.get("", response_model=list[CouponOut])
def list_coupons(db: Session = Depends(get_db)):
    return coupon_service.list_coupons(db)


@router.post(
    "",
    response_model=CouponOut,
    status_code=status.HTTP_201_CREATED,
)
def create_coupon(payload: CouponCreate, db: Session = Depends(get_db)):
    return coupon_service.create_coupon(db, payload)


@router.put("/{coupon_id}", response_model=CouponOut)
def update_coupon(
    coupon_id: int,
    payload: CouponUpdate,
    db: Session = Depends(get_db),
):
    coupon = _require_coupon(coupon_id, db)
    return coupon_service.update_coupon(db, coupon, payload)


@router.delete(
    "/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_coupon(coupon_id: int, db: Session = Depends(get_db)):
    coupon = _require_coupon(coupon_id, db)
    coupon_service.delete_coupon(db, coupon)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
