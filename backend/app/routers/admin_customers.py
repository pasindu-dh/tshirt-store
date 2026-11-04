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
from app.schemas.customer import (
    AdminCustomerDetailOut,
    AdminCustomerOut,
    CustomerStatusUpdate,
)
from app.services import customers as customer_service

router = APIRouter(
    prefix="/admin/customers",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[AdminCustomerOut])
def list_customers(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    customers, total = customer_service.list_customers(
        db,
        page=page,
        limit=limit,
        search=search,
    )
    response.headers["X-Total-Count"] = str(total)
    return customers


@router.patch(
    "/{customer_id}/status",
    response_model=AdminCustomerOut,
)
def update_customer_status(
    customer_id: int,
    payload: CustomerStatusUpdate,
    db: Session = Depends(get_db),
):
    customer = customer_service.set_customer_active(
        db,
        customer_id,
        payload.is_active,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    return customer


@router.get(
    "/{customer_id}",
    response_model=AdminCustomerDetailOut,
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
):
    customer = customer_service.get_customer(
        db, customer_id
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        )

    return customer
