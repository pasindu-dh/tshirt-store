import argparse

from sqlalchemy import delete, func, select
from sqlalchemy.exc import OperationalError

from app.database import SessionLocal
from app.models import Category, Product, ProductImage, ProductVariant
from app.utils.slug import unique_slug

CATEGORIES = [
    "Classic Tees",
    "Graphic Tees",
    "Oversized",
    "Limited Edition",
]

PRODUCTS = [
    {
        "name": "Midnight Essential Tee",
        "category": "Classic Tees",
        "price": 2500,
        "image": "t_shirt_01.jpg",
        "color": "Black",
        "description": "Heavyweight cotton tee with a clean, minimal finish for everyday wear.",
    },
    {
        "name": "Drift Club Graphic Tee",
        "category": "Graphic Tees",
        "price": 3200,
        "image": "t_shirt_02.jpg",
        "color": "Black",
        "description": "Motorsport-inspired graphic print on a soft, breathable cotton base.",
    },
    {
        "name": "Queen Graphic Tee",
        "category": "Graphic Tees",
        "price": 3400,
        "image": "t_shirt_03.jpg",
        "color": "White",
        "description": "Bold front print with a relaxed fit and durable ribbed neckline.",
    },
    {
        "name": "Oversized Cream Sweatshirt",
        "category": "Oversized",
        "price": 4800,
        "image": "t_shirt_04.jpg",
        "color": "Cream",
        "description": "Dropped-shoulder sweatshirt in a brushed cotton blend.",
    },
    {
        "name": "Azure Fleece Zip Jacket",
        "category": "Oversized",
        "price": 6500,
        "image": "t_shirt_05.jpg",
        "color": "Blue",
        "description": "Warm fleece zip-up with a roomy fit for layering.",
    },
    {
        "name": "Olive Relaxed Tee",
        "category": "Classic Tees",
        "price": 2800,
        "image": "t_shirt_06.jpg",
        "color": "Olive",
        "description": "Garment-dyed oversized tee with a soft, broken-in feel.",
    },
    {
        "name": "Hope Street Tee",
        "category": "Graphic Tees",
        "price": 3300,
        "image": "t_shirt_01.jpg",
        "color": "Black",
        "description": "Streetwear graphic tee with a faded vintage finish.",
    },
    {
        "name": "Smoke Wash Tee",
        "category": "Limited Edition",
        "price": 4200,
        "image": "t_shirt_02.jpg",
        "color": "Grey",
        "description": "Acid-wash tee with a one-of-a-kind smoke pattern.",
    },
    {
        "name": "Heritage Script Tee",
        "category": "Classic Tees",
        "price": 2600,
        "image": "t_shirt_03.jpg",
        "color": "White",
        "description": "Classic script logo on a midweight everyday tee.",
    },
    {
        "name": "Boxy Pocket Tee",
        "category": "Oversized",
        "price": 3500,
        "image": "t_shirt_04.jpg",
        "color": "Black",
        "description": "Boxy fit with a chest pocket and reinforced seams.",
    },
    {
        "name": "Cloud Knit Sweatshirt",
        "category": "Oversized",
        "price": 5200,
        "image": "t_shirt_05.jpg",
        "color": "Cream",
        "description": "Soft knit sweatshirt with a relaxed, cloud-like drape.",
    },
    {
        "name": "Sahara Sand Tee",
        "category": "Classic Tees",
        "price": 2700,
        "image": "t_shirt_06.jpg",
        "color": "Sand",
        "description": "Earthy sand tone with a clean crew neck and straight hem.",
    },
    {
        "name": "Neon Grid Tee",
        "category": "Graphic Tees",
        "price": 3600,
        "image": "t_shirt_01.jpg",
        "color": "Black",
        "description": "High-contrast grid print inspired by late-night city lights.",
    },
    {
        "name": "Faded Rose Tee",
        "category": "Limited Edition",
        "price": 4500,
        "image": "t_shirt_02.jpg",
        "color": "Rose",
        "description": "Limited-run tee with a hand-faded rose wash finish.",
    },
    {
        "name": "Court Side Tee",
        "category": "Graphic Tees",
        "price": 3100,
        "image": "t_shirt_03.jpg",
        "color": "Navy",
        "description": "Court-inspired graphic with a comfortable athletic cut.",
    },
    {
        "name": "Everyday Heavy Tee",
        "category": "Classic Tees",
        "price": 2900,
        "image": "t_shirt_04.jpg",
        "color": "Black",
        "description": "Heavyweight 240gsm cotton that holds its shape all day.",
    },
    {
        "name": "Skyline Hooded Sweatshirt",
        "category": "Oversized",
        "price": 5900,
        "image": "t_shirt_05.jpg",
        "color": "Blue",
        "description": "Hooded sweatshirt with a skyline-inspired back print.",
    },
    {
        "name": "Vintage Olive Tee",
        "category": "Limited Edition",
        "price": 3900,
        "image": "t_shirt_06.jpg",
        "color": "Olive",
        "description": "Vintage-washed olive tee with a lived-in texture.",
    },
]

SIZES = ["S", "M", "L", "XL"]
STOCK_BY_SIZE = {"S": 8, "M": 16, "L": 14, "XL": 6}


def seed(reset: bool = False) -> None:
    with SessionLocal() as db:
        if reset:
            db.execute(delete(ProductVariant))
            db.execute(delete(ProductImage))
            db.execute(delete(Product))
            db.execute(delete(Category))
            db.commit()

        existing = db.scalar(select(func.count(Product.id))) or 0

        if existing:
            print(
                f"Database already has {existing} products. "
                "Run `python -m app.seed --reset` to reseed."
            )
            return

        categories = {}

        for name in CATEGORIES:
            category = Category(
                name=name,
                slug=unique_slug(db, Category, name),
            )
            db.add(category)
            categories[name] = category

        db.flush()

        for index, item in enumerate(PRODUCTS, start=1):
            product = Product(
                name=item["name"],
                slug=unique_slug(db, Product, item["name"]),
                description=item["description"],
                price=item["price"],
                category_id=categories[item["category"]].id,
                is_active=True,
            )
            product.images = [
                ProductImage(url=f"/images/{item['image']}", sort_order=0)
            ]
            product.variants = [
                ProductVariant(
                    size=size,
                    color=item["color"],
                    sku=f"FZ-{index:02d}-{size}",
                    stock=STOCK_BY_SIZE[size],
                )
                for size in SIZES
            ]
            db.add(product)

        db.commit()
        print(
            f"Seeded {len(CATEGORIES)} categories "
            f"and {len(PRODUCTS)} products."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the catalog database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing catalog data before seeding.",
    )
    args = parser.parse_args()

    try:
        seed(reset=args.reset)
    except OperationalError as exc:
        raise SystemExit(
            "Database tables were not found. Run `alembic upgrade head` first."
        ) from exc


if __name__ == "__main__":
    main()
