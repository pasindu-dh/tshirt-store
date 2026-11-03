from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Product, WishlistItem


def _wishlist_query(user_id: int):
    return (
        select(WishlistItem)
        .where(WishlistItem.user_id == user_id)
        .options(
            joinedload(WishlistItem.product).joinedload(Product.category),
            joinedload(WishlistItem.product).selectinload(Product.images),
            joinedload(WishlistItem.product).selectinload(
                Product.variants
            ),
        )
        .order_by(WishlistItem.created_at.desc(), WishlistItem.id.desc())
    )


def list_items(db: Session, user_id: int) -> list[WishlistItem]:
    return list(db.scalars(_wishlist_query(user_id)).unique().all())


def add_item(
    db: Session, user_id: int, product_id: int
) -> WishlistItem:
    from fastapi import HTTPException, status

    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    existing = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == product_id,
        )
    )

    if existing is not None:
        return existing

    item = WishlistItem(user_id=user_id, product_id=product_id)
    db.add(item)
    db.commit()

    loaded = db.scalar(
        _wishlist_query(user_id).where(
            WishlistItem.id == item.id
        )
    )

    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Wishlist item could not be loaded",
        )

    return loaded


def remove_item(db: Session, user_id: int, product_id: int) -> None:
    item = db.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == user_id,
            WishlistItem.product_id == product_id,
        )
    )

    if item is not None:
        db.delete(item)
        db.commit()
