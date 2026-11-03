from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Product, Review, User
from app.schemas.review import ReviewCreate, ReviewListOut, ReviewOut


def _to_out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        product_id=review.product_id,
        user_id=review.user_id,
        user_name=review.user.name,
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _review_query(review_id: int | None = None):
    stmt = select(Review).options(joinedload(Review.user))

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


def list_reviews(db: Session, product_id: int) -> ReviewListOut:
    if _get_active_product(db, product_id) is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    reviews = db.scalars(
        select(Review)
        .where(Review.product_id == product_id)
        .options(joinedload(Review.user))
        .order_by(Review.created_at.desc(), Review.id.desc())
    ).all()
    items = [_to_out(review) for review in reviews]
    average = (
        round(sum(review.rating for review in reviews) / len(reviews), 1)
        if reviews
        else 0.0
    )

    return ReviewListOut(items=items, count=len(items), average=average)


def create_review(
    db: Session,
    user: User,
    product_id: int,
    payload: ReviewCreate,
) -> ReviewOut:
    from fastapi import HTTPException, status

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
    from fastapi import HTTPException, status

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
    db.commit()

    updated = _get_review(db, review.id)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Review could not be loaded after update",
        )

    return _to_out(updated)


def delete_review(db: Session, user: User, review_id: int) -> None:
    from fastapi import HTTPException, status

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
