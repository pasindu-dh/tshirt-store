from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Order, User
from app.schemas.return_request import (
    ReturnRequestCreate,
    ReturnRequestOut,
)
from app.services import returns as return_service
from app.services.email import send_return_status_update

router = APIRouter(prefix="/orders", tags=["returns"])


def _customer_order(
    db: Session, user: User, order_id: int
) -> Order:
    order = db.get(Order, order_id)

    if order is None or order.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order


@router.get(
    "/{order_id}/returns",
    response_model=list[ReturnRequestOut],
)
def list_order_returns(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _customer_order(db, current_user, order_id)
    return return_service.list_returns(db, order.id)


@router.post(
    "/{order_id}/returns",
    response_model=ReturnRequestOut,
    status_code=status.HTTP_201_CREATED,
)
def create_order_return(
    order_id: int,
    payload: ReturnRequestCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _customer_order(db, current_user, order_id)
    request = return_service.create_return_request(
        db, current_user, order, payload
    )
    background_tasks.add_task(
        send_return_status_update,
        order.contact_email,
        order.id,
        request.id,
        "requested",
    )
    return request


@router.post(
    "/{order_id}/returns/{return_id}/cancel",
    response_model=ReturnRequestOut,
)
def cancel_order_return(
    order_id: int,
    return_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _customer_order(db, current_user, order_id)
    request = return_service.cancel_return(
        db, current_user, order, return_id
    )
    background_tasks.add_task(
        send_return_status_update,
        order.contact_email,
        order.id,
        request.id,
        "cancelled",
    )
    return request
