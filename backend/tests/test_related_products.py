def _category(client, admin_auth, name):
    response = client.post(
        "/admin/categories",
        headers=admin_auth["headers"],
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_related_products_prefer_the_same_category(
    client, admin_auth, create_product
):
    tees = _category(client, admin_auth, "Related Tees")
    mugs = _category(client, admin_auth, "Related Mugs")

    source = create_product(
        name="Related Source",
        category_id=tees["id"],
        sku_prefix="REL-SRC",
    )
    same_category = create_product(
        name="Related Same Category",
        category_id=tees["id"],
        sku_prefix="REL-SAME",
    )
    other_category = create_product(
        name="Related Other Category",
        category_id=mugs["id"],
        sku_prefix="REL-OTHER",
    )
    inactive = create_product(
        name="Related Inactive",
        category_id=tees["id"],
        is_active=False,
        sku_prefix="REL-INACTIVE",
    )
    create_product(
        name="Related Filler",
        sku_prefix="REL-FILLER",
    )

    response = client.get(
        f"/products/{source['id']}/related",
        params={"limit": 3},
    )
    assert response.status_code == 200, response.text
    ids = [product["id"] for product in response.json()]
    assert ids[0] == same_category["id"]
    assert source["id"] not in ids
    assert inactive["id"] not in ids
    assert other_category["id"] in ids
    assert len(ids) == 3

    limited = client.get(
        f"/products/{source['id']}/related",
        params={"limit": 1},
    )
    assert [item["id"] for item in limited.json()] == [
        same_category["id"]
    ]


def test_related_products_handle_missing_and_inactive(
    client, admin_auth, create_product
):
    inactive = create_product(
        name="Related Hidden", is_active=False
    )

    assert (
        client.get(f"/products/{inactive['id']}/related").status_code
        == 404
    )
    assert (
        client.get("/products/999999/related").status_code == 404
    )
    assert (
        client.get(
            "/products/999999/related",
            params={"limit": 0},
        ).status_code
        == 422
    )


def test_related_products_fill_without_a_category(
    client, create_product
):
    source = create_product(
        name="Related Uncategorised Source",
        sku_prefix="REL-UNCAT",
    )
    other = create_product(
        name="Related Uncategorised Other",
        sku_prefix="REL-UNCAT-2",
    )

    response = client.get(
        f"/products/{source['id']}/related",
        params={"limit": 2},
    )
    assert response.status_code == 200
    ids = [product["id"] for product in response.json()]
    assert other["id"] in ids
    assert source["id"] not in ids
    assert len(ids) == 1
