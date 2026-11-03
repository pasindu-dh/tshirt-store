def test_wishlist_add_list_and_remove(
    client, customer_auth, product
):
    headers = customer_auth["headers"]
    product_id = product["id"]

    added = client.put(
        f"/wishlist/items/{product_id}", headers=headers
    )
    assert added.status_code == 200, added.text
    assert added.json()["product_id"] == product_id
    assert added.json()["product"]["name"] == product["name"]

    added_again = client.put(
        f"/wishlist/items/{product_id}", headers=headers
    )
    assert added_again.status_code == 200

    listing = client.get("/wishlist", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["product_id"] == product_id

    removed = client.delete(
        f"/wishlist/items/{product_id}", headers=headers
    )
    assert removed.status_code == 204
    assert client.get("/wishlist", headers=headers).json() == []

    removed_again = client.delete(
        f"/wishlist/items/{product_id}", headers=headers
    )
    assert removed_again.status_code == 204


def test_wishlist_requires_auth_and_active_product(
    client, customer_auth, create_product
):
    inactive = create_product(name="Hidden Wish", is_active=False)

    anonymous = client.get("/wishlist")
    assert anonymous.status_code == 401

    inactive_response = client.put(
        f"/wishlist/items/{inactive['id']}",
        headers=customer_auth["headers"],
    )
    assert inactive_response.status_code == 404

    missing = client.put(
        "/wishlist/items/999999",
        headers=customer_auth["headers"],
    )
    assert missing.status_code == 404


def test_wishlists_are_private_between_users(
    client, customer_auth, product
):
    other = client.post(
        "/auth/register",
        json={
            "name": "Other Wishlist",
            "email": "wishlist-other@furzy.dev",
            "password": "WishlistPass123!",
        },
    )
    other_headers = {
        "Authorization": f"Bearer {other.json()['access_token']}"
    }

    added = client.put(
        f"/wishlist/items/{product['id']}",
        headers=customer_auth["headers"],
    )
    assert added.status_code == 200

    assert client.get("/wishlist", headers=other_headers).json() == []
    assert (
        client.get("/wishlist", headers=customer_auth["headers"]).json()
        != []
    )
