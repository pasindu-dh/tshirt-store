def _customer_headers(client, email="reviewer@furzy.dev"):
    response = client.post(
        "/auth/register",
        json={
            "name": "Review Customer",
            "email": email,
            "password": "ReviewPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return {
        "Authorization": f"Bearer {response.json()['access_token']}"
    }


def test_review_lifecycle(client, customer_auth, product):
    headers = customer_auth["headers"]
    product_id = product["id"]

    created = client.post(
        f"/reviews/product/{product_id}",
        headers=headers,
        json={
            "rating": 5,
            "title": "Great quality",
            "comment": "Soft fabric and a good fit.",
        },
    )
    assert created.status_code == 201, created.text
    review = created.json()
    assert review["rating"] == 5
    assert review["user_name"] == "Test Customer"
    assert review["product_id"] == product_id

    duplicate = client.post(
        f"/reviews/product/{product_id}",
        headers=headers,
        json={"rating": 4, "comment": "Again"},
    )
    assert duplicate.status_code == 409

    public = client.get(f"/reviews/product/{product_id}")
    assert public.status_code == 200
    summary = public.json()
    assert summary["count"] == 1
    assert summary["average"] == 5.0
    assert summary["items"][0]["id"] == review["id"]

    updated = client.put(
        f"/reviews/{review['id']}",
        headers=headers,
        json={
            "rating": 4,
            "title": "Still good",
            "comment": "Updated after a week.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["rating"] == 4
    assert updated.json()["title"] == "Still good"

    summary_after_update = client.get(
        f"/reviews/product/{product_id}"
    ).json()
    assert summary_after_update["average"] == 4.0

    other_headers = _customer_headers(client, "other-reviewer@furzy.dev")
    forbidden = client.put(
        f"/reviews/{review['id']}",
        headers=other_headers,
        json={"rating": 1, "comment": "Not mine"},
    )
    assert forbidden.status_code == 403

    deleted = client.delete(
        f"/reviews/{review['id']}", headers=headers
    )
    assert deleted.status_code == 204
    assert client.get(f"/reviews/product/{product_id}").json()["count"] == 0

    missing = client.delete(
        f"/reviews/{review['id']}", headers=headers
    )
    assert missing.status_code == 404


def test_review_validation_auth_and_product_checks(
    client, customer_auth, create_product
):
    inactive = create_product(name="Unreviewable Tee", is_active=False)

    anonymous = client.post(
        f"/reviews/product/{inactive['id']}",
        json={"rating": 5},
    )
    assert anonymous.status_code == 401

    inactive_response = client.post(
        f"/reviews/product/{inactive['id']}",
        headers=customer_auth["headers"],
        json={"rating": 5},
    )
    assert inactive_response.status_code == 404

    missing_product = client.get("/reviews/product/999999")
    assert missing_product.status_code == 404

    invalid_rating = client.post(
        f"/reviews/product/{inactive['id']}",
        headers=customer_auth["headers"],
        json={"rating": 6},
    )
    assert invalid_rating.status_code == 422


def test_admin_can_moderate_reviews(
    client, admin_auth, customer_auth, product
):
    created = client.post(
        f"/reviews/product/{product['id']}",
        headers=customer_auth["headers"],
        json={"rating": 3, "comment": "Needs moderation"},
    )
    assert created.status_code == 201

    deleted = client.delete(
        f"/reviews/{created.json()['id']}",
        headers=admin_auth["headers"],
    )
    assert deleted.status_code == 204
