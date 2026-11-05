from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Product, Review, User
from app.schemas.review import (
    AdminReviewOut,
    ReviewCreate,
    ReviewListOut,
    ReviewOut,
)

PUBLIC_REVIEW_STATUSES = ("published",)


def _to_out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        product_id=review.product_id,
        user_id=review.user_id,
        user_name=review.user.name,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        status=review.status,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _to_admin_out(review: Review) -> AdminReviewOut:
    return AdminReviewOut(
        id=review.id,
        product_id=review.product_id,
        product_name=review.product.name,
        product_slug=review.product.slug,
        user_id=review.user_id,
        user_name=review.user.name,
        user_email=review.user.email,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        status=review.status,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _review_query(review_id: int | None = None):
    stmt = select(Review).options(
        joinedload(Review.user),
        joinedload(Review.product),
    )

    if review_id is not None:
        stmt = stmt.where(Review.id == review_id)

    return stmt


def _get_review(db: Session, review_id: int) -> Review | None:
    return db.scalar(_review_query(review_id))


def _get_active_product(db: Session, product_id: int) -> Product | None:
    return db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
    )


def list_reviews(
    db: Session,
    product_id: int,
    *,
    viewer: User | None = None,
) -> ReviewListOut:
    if _get_active_product(db, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    reviews = db.scalars(
        select(Review)
        .where(
            Review.product_id == product_id,
            Review.status.in_(PUBLIC_REVIEW_STATUSES),
        )
        .options(joinedload(Review.user))
        .order_by(Review.created_at.desc(), Review.id.desc())
    ).all()
    items = [_to_out(review) for review in reviews]
    average = (
        round(sum(review.rating for review in reviews) / len(reviews), 1)
        if reviews
        else 0.0
    )
    my_review = None

    if viewer is not None:
        mine = db.scalar(
            select(Review)
            .where(
                Review.product_id == product_id,
                Review.user_id == viewer.id,
            )
            .options(joinedload(Review.user))
        )

        if mine is not None:
            my_review = _to_out(mine)

    return ReviewListOut(
        items=items,
        count=len(items),
        average=average,
        my_review=my_review,
    )


def create_review(
    db: Session,
    user: User,
    product_id: int,
    payload: ReviewCreate,
) -> ReviewOut:
    if _get_active_product(db, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    existing = db.scalar(
        select(Review).where(
            Review.product_id == product_id,
            Review.user_id == user.id,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this product",
        )

    review = Review(
        product_id=product_id,
        user_id=user.id,
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
        status=(
            "pending"
            if settings.review_moderation_enabled
            else "published"
        ),
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    created = _get_review(db, review.id)

    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review could not be loaded after creation",
        )

    return _to_out(created)


def update_review(
    db: Session,
    user: User,
    review_id: int,
    payload: ReviewCreate,
) -> ReviewOut:
    review = _get_review(db, review_id)

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if review.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own reviews",
        )

    review.rating = payload.rating
    review.title = payload.title
    review.comment = payload.comment
    review.status = (
        "pending"
        if settings.review_moderation_enabled
        else "published"
    )
    db.commit()

    updated = _get_review(db, review.id)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review could not be loaded after update",
        )

    return _to_out(updated)


def delete_review(db: Session, user: User, review_id: int) -> None:
    review = _get_review(db, review_id)

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if review.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews",
        )

    db.delete(review)
    db.commit()


def list_admin_reviews(
    db: Session,
    *,
    page: int,
    limit: int,
    status_filter: str | None = None,
    search: str | None = None,
    rating: int | None = None,
) -> tuple[list[AdminReviewOut], int]:
    filters = []

    if status_filter:
        filters.append(Review.status == status_filter)

    if rating is not None:
        filters.append(Review.rating == rating)

    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(term),
                User.name.ilike(term),
                User.email.ilike(term),
                Review.title.ilike(term),
                Review.comment.ilike(term),
            )
        )

    total = int(
        db.scalar(
            select(func.count(Review.id))
            .join(Product, Review.product_id == Product.id)
            .join(User, Review.user_id == User.id)
            .where(*filters)
        )
        or 0
    )
    reviews = db.scalars(
        select(Review)
        .join(Product, Review.product_id == Product.id)
        .join(User, Review.user_id == User.id)
        .where(*filters)
        .options(
            joinedload(Review.user),
            joinedload(Review.product),
        )
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return [_to_admin_out(review) for review in reviews], total


def set_admin_review_status(
    db: Session,
    review_id: int,
    new_status: str,
) -> AdminReviewOut:
    review = _get_review(db, review_id)

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    review.status = new_status
    db.commit()
    db.refresh(review)

    updated = _get_review(db, review.id)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review could not be loaded after update",
        )

    return _to_admin_out(updated)
