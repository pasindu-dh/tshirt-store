import csv
import io

from app.services.catalog_import import CATALOG_HEADERS


def _csv_bytes(rows, headers=None):
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=headers or CATALOG_HEADERS
    )
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _row(**overrides):
    values = {
        "product_slug": "",
        "product_name": "CSV Tee",
        "description": "Imported tee",
        "price": "2500",
        "category_slug": "",
        "is_active": "true",
        "image_urls": "/images/test.jpg",
        "variant_size": "M",
        "variant_color": "Black",
        "variant_sku": "CSV-M",
        "variant_stock": "5",
        "variant_low_stock_threshold": "5",
    }
    values.update(overrides)
    return values


def _import(client, admin_auth, payload, *, dry_run):
    return client.post(
        "/admin/products/import",
        headers=admin_auth["headers"],
        params={"dry_run": "true" if dry_run else "false"},
        files={
            "file": ("catalog.csv", payload, "text/csv"),
        },
    )


def _admin_products(client, admin_auth, search):
    response = client.get(
        "/admin/products",
        headers=admin_auth["headers"],
        params={"search": search},
    )
    assert response.status_code == 200
    return response.json()


def test_catalog_export_and_new_product_import(
    client,
    admin_auth,
    customer_auth,
    product,
):
    category = client.post(
        "/admin/categories",
        headers=admin_auth["headers"],
        json={"name": "Imported Category"},
    )
    assert category.status_code == 201
    category_slug = category.json()["slug"]

    export = client.get(
        "/admin/exports/products.csv",
        headers=admin_auth["headers"],
    )
    assert export.status_code == 200
    rows = list(
        csv.DictReader(io.StringIO(export.text))
    )
    assert rows
    assert any(
        row["product_slug"] == product["slug"]
        and row["variant_sku"] == product["variants"][0]["sku"]
        for row in rows
    )

    customer_export = client.get(
        "/admin/exports/products.csv",
        headers=customer_auth["headers"],
    )
    anonymous_export = client.get(
        "/admin/exports/products.csv"
    )
    assert customer_export.status_code == 403
    assert anonymous_export.status_code == 401

    payload = _csv_bytes(
        [
            _row(
                product_name="Imported Tee",
                price="3000",
                category_slug=category_slug,
                image_urls="/images/a.jpg|/images/b.jpg",
                variant_sku="IMPORT-M",
                variant_stock="7",
                variant_low_stock_threshold="3",
            ),
            _row(
                product_name="Imported Tee",
                price="3000",
                category_slug=category_slug,
                image_urls="/images/a.jpg|/images/b.jpg",
                variant_size="L",
                variant_sku="IMPORT-L",
                variant_stock="2",
                variant_low_stock_threshold="5",
            ),
        ]
    )

    preview = _import(
        client, admin_auth, payload, dry_run=True
    )
    assert preview.status_code == 200, preview.text
    preview_data = preview.json()
    assert preview_data["valid"] is True
    assert preview_data["summary"]["products_create"] == 1
    assert preview_data["summary"]["variants_create"] == 2
    assert _admin_products(
        client, admin_auth, "Imported Tee"
    ) == []

    applied = _import(
        client, admin_auth, payload, dry_run=False
    )
    assert applied.status_code == 200, applied.text
    applied_data = applied.json()
    assert applied_data["valid"] is True
    assert applied_data["summary"]["error_rows"] == 0

    products = _admin_products(
        client, admin_auth, "Imported Tee"
    )
    assert len(products) == 1
    imported = products[0]
    assert imported["name"] == "Imported Tee"
    assert imported["price"] == 3000
    assert imported["category"]["slug"] == category_slug
    assert [
        image["url"] for image in imported["images"]
    ] == [
        "/images/a.jpg",
        "/images/b.jpg",
    ]
    assert len(imported["variants"]) == 2
    variants = {
        variant["size"]: variant
        for variant in imported["variants"]
    }
    assert variants["M"]["sku"] == "IMPORT-M"
    assert variants["M"]["stock"] == 7
    assert variants["M"]["low_stock_threshold"] == 3
    assert variants["L"]["stock"] == 2

    movements = client.get(
        "/admin/inventory/movements",
        headers=admin_auth["headers"],
        params={
            "product_id": imported["id"],
            "movement_type": "initial_stock",
        },
    )
    assert movements.status_code == 200
    assert movements.headers["X-Total-Count"] == "2"

    customer_import = _import(
        client, customer_auth, payload, dry_run=True
    )
    anonymous_import = client.post(
        "/admin/products/import",
        params={"dry_run": "true"},
        files={
            "file": ("catalog.csv", payload, "text/csv"),
        },
    )
    assert customer_import.status_code == 403
    assert anonymous_import.status_code == 401


def test_catalog_import_updates_existing_product_without_removing_variants(
    client,
    admin_auth,
    product,
):
    category = client.post(
        "/admin/categories",
        headers=admin_auth["headers"],
        json={"name": "Updated Category"},
    )
    assert category.status_code == 201
    category_slug = category.json()["slug"]
    medium = next(
        variant
        for variant in product["variants"]
        if variant["size"] == "M"
    )
    large = next(
        variant
        for variant in product["variants"]
        if variant["size"] == "L"
    )

    payload = _csv_bytes(
        [
            _row(
                product_slug=product["slug"],
                product_name="Renamed CSV Tee",
                description="Updated via CSV",
                price="3100",
                category_slug=category_slug,
                image_urls="/images/test.jpg",
                variant_size="M",
                variant_color="Black",
                variant_sku=medium["sku"],
                variant_stock="5",
                variant_low_stock_threshold="4",
            )
        ]
    )

    preview = _import(
        client, admin_auth, payload, dry_run=True
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] is True
    assert preview.json()["summary"]["products_update"] == 1
    assert preview.json()["summary"]["variants_update"] == 1
    assert preview.json()["summary"]["variants_create"] == 0

    applied = _import(
        client, admin_auth, payload, dry_run=False
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["valid"] is True

    fetched = client.get(
        f"/admin/products/{product['id']}",
        headers=admin_auth["headers"],
    )
    assert fetched.status_code == 200
    data = fetched.json()
    assert data["name"] == "Renamed CSV Tee"
    assert data["description"] == "Updated via CSV"
    assert data["price"] == 3100
    assert data["category"]["slug"] == category_slug
    assert len(data["variants"]) == 2

    updated_medium = next(
        variant
        for variant in data["variants"]
        if variant["size"] == "M"
    )
    updated_large = next(
        variant
        for variant in data["variants"]
        if variant["size"] == "L"
    )
    assert updated_medium["id"] == medium["id"]
    assert updated_medium["stock"] == 5
    assert updated_medium["low_stock_threshold"] == 4
    assert updated_large["id"] == large["id"]
    assert updated_large["stock"] == large["stock"]


def test_catalog_import_validation_errors(
    client,
    admin_auth,
    customer_auth,
):
    rows = [
        _row(
            product_name="Bad Category",
            category_slug="missing-category",
            variant_sku="BAD-CAT",
        ),
        _row(
            product_name="Bad Price",
            price="free",
            variant_sku="BAD-PRICE",
        ),
        _row(
            product_slug="missing-product",
            product_name="Bad Slug",
            variant_sku="BAD-SLUG",
        ),
        _row(
            product_name="Duplicate SKU",
            variant_sku="DUP-SKU",
        ),
        _row(
            product_name="Duplicate SKU",
            variant_size="L",
            variant_sku="DUP-SKU",
        ),
        _row(
            product_name="Duplicate Variant",
            variant_sku="DUP-VAR-1",
        ),
        _row(
            product_name="Duplicate Variant",
            variant_sku="DUP-VAR-2",
        ),
    ]
    payload = _csv_bytes(rows)

    preview = _import(
        client, admin_auth, payload, dry_run=True
    )
    assert preview.status_code == 200
    preview_data = preview.json()
    assert preview_data["valid"] is False
    assert preview_data["summary"]["error_rows"] >= 5
    assert any(
        "Unknown category_slug"
        in row["message"]
        for row in preview_data["rows"]
    )
    assert any(
        "price" in row["message"]
        for row in preview_data["rows"]
    )
    assert any(
        "was not found" in row["message"]
        for row in preview_data["rows"]
    )
    assert any(
        "Duplicate variant SKU"
        in row["message"]
        for row in preview_data["rows"]
    )
    assert any(
        "Duplicate size/color"
        in row["message"]
        for row in preview_data["rows"]
    )

    applied = _import(
        client, admin_auth, payload, dry_run=False
    )
    assert applied.status_code == 200
    assert applied.json()["valid"] is False
    assert _admin_products(
        client, admin_auth, "Duplicate SKU"
    ) == []
    assert _admin_products(
        client, admin_auth, "Duplicate Variant"
    ) == []

    missing_headers = client.post(
        "/admin/products/import",
        headers=admin_auth["headers"],
        params={"dry_run": "true"},
        files={
            "file": (
                "catalog.csv",
                b"product_name,price\nTest,100\n",
                "text/csv",
            )
        },
    )
    assert missing_headers.status_code == 200
    assert missing_headers.json()["valid"] is False
    assert "Missing required column" in (
        missing_headers.json()["rows"][0]["message"]
    )

    customer_import = _import(
        client, customer_auth, payload, dry_run=True
    )
    anonymous_import = client.post(
        "/admin/products/import",
        params={"dry_run": "true"},
        files={
            "file": ("catalog.csv", payload, "text/csv"),
        },
    )
    assert customer_import.status_code == 403
    assert anonymous_import.status_code == 401
