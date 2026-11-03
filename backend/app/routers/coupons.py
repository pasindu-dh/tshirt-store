from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.coupon import CouponPreviewOut, CouponPreviewRequest
from app.services import coupons as coupon_service

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.post("/preview", response_model=CouponPreviewOut)
def preview_coupon(
    payload: CouponPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return coupon_service.preview(db, current_user.id, payload.code)
