from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import User
from app.schemas.inventory import (
    LowStockVariantOut,
    StockAdjustmentOut,
    StockAdjustmentRequest,
    StockMovementOut,
    StockMovementType,
)
from app.services import inventory

router = APIRouter(
    prefix="/admin/inventory",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/low-stock", response_model=list[LowStockVariantOut]
)
def list_low_stock(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    variants, total = inventory.list_low_stock(
        db,
        page=page,
        limit=limit,
        search=search,
    )
    response.headers["X-Total-Count"] = str(total)
    return variants


@router.get(
    "/movements", response_model=list[StockMovementOut]
)
def list_stock_movements(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    movement_type: StockMovementType | None = Query(None),
    variant_id: int | None = Query(None, ge=1),
    product_id: int | None = Query(None, ge=1),
    order_id: int | None = Query(None, ge=1),
    search: str | None = Query(None, max_length=100),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be on or before date_to.",
        )

    movements, total = inventory.list_movements(
        db,
        page=page,
        limit=limit,
        movement_type=movement_type,
        variant_id=variant_id,
        product_id=product_id,
        order_id=order_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    response.headers["X-Total-Count"] = str(total)
    return movements


@router.post(
    "/variants/{variant_id}/adjust",
    response_model=StockAdjustmentOut,
)
def adjust_variant_stock(
    variant_id: int,
    payload: StockAdjustmentRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    variant, movement = inventory.adjust_stock(
        db,
        variant_id,
        payload,
        actor_user_id=current_user.id,
    )
    return StockAdjustmentOut(
        variant=inventory.low_stock_variant_out(variant),
        movement=movement,
    )
