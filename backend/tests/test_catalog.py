def test_catalog_list_search_sort_and_slug(
    client, admin_auth, create_product
):
    alpha = create_product(name="Alpha Tee", price=1500)
    beta = create_product(name="Beta Tee", price=3000)
    hidden = create_product(
        name="Hidden Tee", price=1000, is_active=False
    )

    listing = client.get("/products")
    assert listing.status_code == 200
    assert listing.headers["X-Total-Count"] == "2"
    listed_ids = {item["id"] for item in listing.json()}
    assert alpha["id"] in listed_ids
    assert beta["id"] in listed_ids
    assert hidden["id"] not in listed_ids

    search = client.get("/products", params={"search": "Alpha"})
    assert [item["id"] for item in search.json()] == [alpha["id"]]

    sorted_products = client.get(
        "/products", params={"sort": "price_asc"}
    )
    prices = [item["price"] for item in sorted_products.json()]
    assert prices == sorted(prices)

    by_slug = client.get(f"/products/slug/{alpha['slug']}")
    assert by_slug.status_code == 200
    assert by_slug.json()["id"] == alpha["id"]

    hidden_by_slug = client.get(f"/products/slug/{hidden['slug']}")
    hidden_by_id = client.get(f"/products/{hidden['id']}")
    assert hidden_by_slug.status_code == 404
    assert hidden_by_id.status_code == 404

    admin_listing = client.get(
        "/admin/products", headers=admin_auth["headers"]
    )
    assert admin_listing.status_code == 200
    assert admin_listing.headers["X-Total-Count"] == "3"


def test_category_filter_and_delete_guard(
    client, admin_auth, create_product
):
    category = client.post(
        "/admin/categories",
        headers=admin_auth["headers"],
        json={"name": "Hoodies"},
    )
    assert category.status_code == 201, category.text
    category_data = category.json()

    product = create_product(category_id=category_data["id"])
    assert product["category"]["slug"] == category_data["slug"]

    filtered = client.get(
        "/products", params={"category": category_data["slug"]}
    )
    assert [item["id"] for item in filtered.json()] == [product["id"]]

    blocked_delete = client.delete(
        f"/admin/categories/{category_data['id']}",
        headers=admin_auth["headers"],
    )
    assert blocked_delete.status_code == 409

    deleted_product = client.delete(
        f"/admin/products/{product['id']}",
        headers=admin_auth["headers"],
    )
    assert deleted_product.status_code == 204

    deleted_category = client.delete(
        f"/admin/categories/{category_data['id']}",
        headers=admin_auth["headers"],
    )
    assert deleted_category.status_code == 204


def test_product_update_with_existing_variant_skus(
    client, admin_auth, product
):
    variants = [
        {
            "size": variant["size"],
            "color": variant["color"],
            "sku": variant["sku"],
            "stock": 4 if variant["size"] == "M" else 3,
        }
        for variant in product["variants"]
    ]

    updated = client.put(
        f"/admin/products/{product['id']}",
        headers=admin_auth["headers"],
        json={
            "name": "Updated Tee",
            "price": 3200,
            "variants": variants,
        },
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data["name"] == "Updated Tee"
    assert data["price"] == 3200
    assert {variant["stock"] for variant in data["variants"]} == {4, 3}
    assert {variant["sku"] for variant in data["variants"]} == {
        variant["sku"] for variant in product["variants"]
    }

    fetched = client.get(
        f"/admin/products/{product['id']}",
        headers=admin_auth["headers"],
    )
    assert fetched.status_code == 200
    assert fetched.json()["price"] == 3200
