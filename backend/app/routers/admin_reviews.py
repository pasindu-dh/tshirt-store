from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import User
from app.schemas.review import (
    AdminReviewOut,
    AdminReviewStatusUpdate,
)
from app.services import reviews as review_service

ReviewStatusFilter = Literal["pending", "published", "rejected"]

router = APIRouter(
    prefix="/admin/reviews",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[AdminReviewOut])
def list_admin_reviews(
    response: Response,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: ReviewStatusFilter | None = Query(
        None, alias="status"
    ),
    search: str | None = Query(None, max_length=100),
    rating: int | None = Query(None, ge=1, le=5),
    db: Session = Depends(get_db),
):
    reviews, total = review_service.list_admin_reviews(
        db,
        page=page,
        limit=limit,
        status_filter=status_filter,
        search=search,
        rating=rating,
    )
    response.headers["X-Total-Count"] = str(total)
    return reviews


@router.patch(
    "/{review_id}", response_model=AdminReviewOut
)
def update_admin_review_status(
    review_id: int,
    payload: AdminReviewStatusUpdate,
    db: Session = Depends(get_db),
):
    return review_service.set_admin_review_status(
        db, review_id, payload.status
    )


@router.delete(
    "/{review_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_admin_review(
    review_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    review_service.delete_review(db, current_user, review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
