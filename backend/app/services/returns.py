from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, Refund, ReturnRequest, User
from app.models.common import utcnow
from app.schemas.return_request import (
    ReturnLinkRefundRequest,
    ReturnRequestCreate,
    ReturnReviewRequest,
)


def _return_query(order_id: int):
    return (
        select(ReturnRequest)
        .where(ReturnRequest.order_id == order_id)
        .options(selectinload(ReturnRequest.refund))
        .order_by(ReturnRequest.id.desc())
    )


def list_returns(
    db: Session, order_id: int
) -> list[ReturnRequest]:
    return list(db.scalars(_return_query(order_id)).all())


def get_return(
    db: Session, order_id: int, return_id: int
) -> ReturnRequest | None:
    return db.scalar(
        _return_query(order_id).where(
            ReturnRequest.id == return_id
        )
    )


def create_return_request(
    db: Session,
    user: User,
    order: Order,
    payload: ReturnRequestCreate,
) -> ReturnRequest:
    from fastapi import HTTPException, status

    if order.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status != "delivered":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Returns can only be requested after the order is "
                "delivered."
            ),
        )

    active = db.scalar(
        select(ReturnRequest).where(
            ReturnRequest.order_id == order.id,
            ReturnRequest.status.in_(("requested", "approved")),
        )
    )

    if active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order already has an active return request.",
        )

    request = ReturnRequest(
        order_id=order.id,
        user_id=user.id,
        status="requested",
        reason=payload.reason.strip(),
        notes=payload.notes.strip(),
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return request


def review_return(
    db: Session,
    admin_user: User,
    order: Order,
    return_id: int,
    payload: ReturnReviewRequest,
) -> ReturnRequest:
    from fastapi import HTTPException, status

    request = get_return(db, order.id, return_id)

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found.",
        )

    if request.status != "requested":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This return request has already been reviewed.",
        )

    request.status = payload.status
    request.review_note = payload.note.strip()
    request.reviewed_by_user_id = admin_user.id
    request.reviewed_at = utcnow()
    db.commit()
    db.refresh(request)
    return request


def link_refund(
    db: Session,
    order: Order,
    return_id: int,
    payload: ReturnLinkRefundRequest,
) -> ReturnRequest:
    from fastapi import HTTPException, status

    request = get_return(db, order.id, return_id)

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found.",
        )

    if request.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approve the return request before linking a refund.",
        )

    refund = db.scalar(
        select(Refund).where(
            Refund.id == payload.refund_id,
            Refund.order_id == order.id,
        )
    )

    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found for this order.",
        )

    request.refund_id = refund.id
    db.commit()
    db.refresh(request)
    return request
