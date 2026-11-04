from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Order,
    OrderItem,
    ProductVariant,
    Refund,
    ReturnItem,
    ReturnRequest,
    User,
)
from app.models.common import utcnow
from app.schemas.return_request import (
    AdminReturnQueueOut,
    ReturnLinkRefundRequest,
    ReturnRequestCreate,
    ReturnReviewRequest,
)

RETURNED_STATUSES = ("requested", "approved", "completed")


def _return_query(order_id: int):
    return (
        select(ReturnRequest)
        .where(ReturnRequest.order_id == order_id)
        .options(
            selectinload(ReturnRequest.refund),
            selectinload(ReturnRequest.items),
        )
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


def _get_return_for_update(
    db: Session, order_id: int, return_id: int
) -> ReturnRequest | None:
    return db.scalar(
        select(ReturnRequest)
        .where(
            ReturnRequest.order_id == order_id,
            ReturnRequest.id == return_id,
        )
        .options(
            selectinload(ReturnRequest.refund),
            selectinload(ReturnRequest.items),
        )
        .with_for_update()
    )


def _already_returned(
    db: Session, order_id: int, order_item_id: int
) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(ReturnItem.quantity), 0))
            .join(ReturnRequest)
            .where(
                ReturnRequest.order_id == order_id,
                ReturnItem.order_item_id == order_item_id,
                ReturnRequest.status.in_(RETURNED_STATUSES),
            )
        )
        or 0
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

    # Serialize return creation per order so concurrent requests cannot
    # both pass the one-active-return and remaining-quantity checks.
    order = (
        db.scalar(
            select(Order)
            .where(Order.id == order.id)
            .with_for_update()
        )
        or order
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

    items = []

    for entry in payload.items:
        order_item = db.get(OrderItem, entry.order_item_id)

        if order_item is None or order_item.order_id != order.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "One or more selected items do not belong to this "
                    "order."
                ),
            )

        already_returned = _already_returned(
            db, order.id, order_item.id
        )
        remaining = order_item.quantity - already_returned

        if entry.quantity > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Only {remaining} of {order_item.product_name} "
                    f"({order_item.size}/{order_item.color}) can be "
                    "returned."
                ),
            )

        items.append(
            ReturnItem(
                order_item_id=order_item.id,
                variant_id=order_item.variant_id,
                quantity=entry.quantity,
                product_name=order_item.product_name,
                size=order_item.size,
                color=order_item.color,
                sku=order_item.sku,
            )
        )

    request = ReturnRequest(
        order_id=order.id,
        user_id=user.id,
        status="requested",
        reason=payload.reason.strip(),
        notes=payload.notes.strip(),
        items=items,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    return get_return(db, order.id, request.id) or request


def _restock_items(
    db: Session,
    request: ReturnRequest,
    note: str,
) -> None:
    if request.stock_restocked_at is not None:
        return

    variant_ids = [
        item.variant_id
        for item in request.items
        if item.variant_id is not None
    ]

    if variant_ids:
        variants = db.scalars(
            select(ProductVariant)
            .where(ProductVariant.id.in_(variant_ids))
            .order_by(ProductVariant.id)
            .with_for_update()
        ).all()
        variants_by_id = {
            variant.id: variant for variant in variants
        }

        for item in request.items:
            variant = (
                variants_by_id.get(item.variant_id)
                if item.variant_id is not None
                else None
            )

            if variant is not None:
                variant.stock += item.quantity
                item.restocked_at = utcnow()

    request.stock_restocked_at = utcnow()
    request.completed_at = utcnow()
    request.status = "completed"
    request.review_note = (
        f"{request.review_note}\n{note}".strip()
        if note
        else request.review_note
    )


def review_return(
    db: Session,
    admin_user: User,
    order: Order,
    return_id: int,
    payload: ReturnReviewRequest,
) -> ReturnRequest:
    from fastapi import HTTPException, status

    request = _get_return_for_update(
        db, order.id, return_id
    )

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found.",
        )

    next_status = payload.status

    if request.status == "requested":
        if next_status not in {"approved", "rejected"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Approve or reject the return before completing "
                    "it."
                ),
            )
    elif request.status == "approved":
        if next_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An approved return can only be marked completed."
                ),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This return request can no longer be changed.",
        )

    request.reviewed_by_user_id = admin_user.id
    request.reviewed_at = utcnow()

    if payload.note.strip():
        request.review_note = (
            f"{request.review_note}\n{payload.note.strip()}".strip()
        )

    if next_status == "completed":
        _restock_items(db, request, "Return completed and items restocked.")
    else:
        request.status = next_status

    db.commit()
    db.refresh(request)
    return get_return(db, order.id, request.id) or request


def cancel_return(
    db: Session,
    user: User,
    order: Order,
    return_id: int,
) -> ReturnRequest:
    from fastapi import HTTPException, status

    request = _get_return_for_update(
        db, order.id, return_id
    )

    if request is None or request.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found.",
        )

    if request.status != "requested":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only a pending return request can be cancelled by "
                "the customer."
            ),
        )

    request.status = "cancelled"
    db.commit()
    db.refresh(request)
    return get_return(db, order.id, request.id) or request


def link_refund(
    db: Session,
    order: Order,
    return_id: int,
    payload: ReturnLinkRefundRequest,
) -> ReturnRequest:
    from fastapi import HTTPException, status

    request = _get_return_for_update(
        db, order.id, return_id
    )

    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found.",
        )

    if request.status not in {"approved", "completed"}:
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
    return get_return(db, order.id, request.id) or request


def list_admin_returns(
    db: Session,
    *,
    page: int,
    limit: int,
    status_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[AdminReturnQueueOut], int]:
    filters = []

    if status_filter:
        filters.append(ReturnRequest.status == status_filter)

    if search and search.strip():
        term_value = search.strip()

        if term_value.isdigit():
            filters.append(
                or_(
                    ReturnRequest.id == int(term_value),
                    ReturnRequest.order_id == int(term_value),
                )
            )
        else:
            term = f"%{term_value}%"
            filters.append(
                or_(
                    Order.contact_name.ilike(term),
                    Order.contact_email.ilike(term),
                    ReturnRequest.reason.ilike(term),
                )
            )

    total = (
        db.scalar(
            select(func.count(ReturnRequest.id))
            .join(Order, ReturnRequest.order_id == Order.id)
            .where(*filters)
        )
        or 0
    )
    rows = db.execute(
        select(ReturnRequest, Order)
        .join(Order, ReturnRequest.order_id == Order.id)
        .where(*filters)
        .options(
            selectinload(ReturnRequest.items),
            selectinload(ReturnRequest.refund),
        )
        .order_by(
            ReturnRequest.created_at.desc(),
            ReturnRequest.id.desc(),
        )
        .offset((page - 1) * limit)
        .limit(limit)
    ).unique().all()

    items = [
        AdminReturnQueueOut(
            id=request.id,
            order_id=request.order_id,
            status=request.status,
            reason=request.reason,
            created_at=request.created_at,
            order_contact_name=order.contact_name,
            order_contact_email=order.contact_email,
            order_total=order.total,
            item_count=sum(item.quantity for item in request.items),
            refund_id=request.refund_id,
            refund_status=(
                request.refund.status if request.refund else None
            ),
        )
        for request, order in rows
    ]

    return items, total
