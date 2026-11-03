from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.review import ReviewCreate, ReviewListOut, ReviewOut
from app.services import reviews as review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get(
    "/product/{product_id}",
    response_model=ReviewListOut,
)
def list_product_reviews(
    product_id: int,
    db: Session = Depends(get_db),
):
    return review_service.list_reviews(db, product_id)


@router.post(
    "/product/{product_id}",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product_review(
    product_id: int,
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_service.create_review(
        db, current_user, product_id, payload
    )


@router.put("/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: int,
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return review_service.update_review(
        db, current_user, review_id, payload
    )


@router.delete(
    "/{review_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review_service.delete_review(db, current_user, review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
