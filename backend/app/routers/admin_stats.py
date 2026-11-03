from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.schemas.order import AdminOrderStatsOut
from app.services import admin_orders

router = APIRouter(
    prefix="/admin/stats",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=AdminOrderStatsOut)
def get_admin_stats(db: Session = Depends(get_db)):
    return admin_orders.get_stats(db)
