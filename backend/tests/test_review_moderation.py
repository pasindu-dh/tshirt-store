from app.config import settings


def _review(client, headers, product_id, **overrides):
    payload = {
        "rating": 4,
        "title": "Moderated review",
        "comment": "Please review this content.",
        **overrides,
    }
    return client.post(
        f"/reviews/product/{product_id}",
        headers=headers,
        json=payload,
    )


def test_review_moderation_queue_and_publishing(
    client, admin_auth, customer_auth, product, monkeypatch
):
    monkeypatch.setattr(
        settings, "review_moderation_enabled", True
    )

    created = _review(
        client, customer_auth["headers"], product["id"]
    )
    assert created.status_code == 201, created.text
    review = created.json()
    assert review["status"] == "pending"

    public = client.get(
        f"/reviews/product/{product['id']}"
    ).json()
    assert public["count"] == 0
    assert public["average"] == 0.0
    assert public["items"] == []
    assert public["my_review"] is None

    mine = client.get(
        f"/reviews/product/{product['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert mine["my_review"]["id"] == review["id"]
    assert mine["my_review"]["status"] == "pending"

    queue = client.get(
        "/admin/reviews",
        headers=admin_auth["headers"],
        params={"status": "pending", "search": "moderated"},
    )
    assert queue.status_code == 200, queue.text
    assert int(queue.headers["X-Total-Count"]) == 1
    row = queue.json()[0]
    assert row["product_name"] == product["name"]
    assert row["user_email"] == "customer@furzy.dev"
    assert row["status"] == "pending"

    published = client.patch(
        f"/admin/reviews/{review['id']}",
        headers=admin_auth["headers"],
        json={"status": "published"},
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    live = client.get(
        f"/reviews/product/{product['id']}"
    ).json()
    assert live["count"] == 1
    assert live["average"] == 4.0
    assert live["items"][0]["id"] == review["id"]

    edited = client.put(
        f"/reviews/{review['id']}",
        headers=customer_auth["headers"],
        json={
            "rating": 5,
            "title": "Updated review",
            "comment": "Edited content needs review again.",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "pending"
    assert (
        client.get(f"/reviews/product/{product['id']}").json()[
            "count"
        ]
        == 0
    )

    rejected = client.patch(
        f"/admin/reviews/{review['id']}",
        headers=admin_auth["headers"],
        json={"status": "rejected"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    customer_view = client.get(
        f"/reviews/product/{product['id']}",
        headers=customer_auth["headers"],
    ).json()
    assert customer_view["my_review"]["status"] == "rejected"
    assert customer_view["count"] == 0

    deleted = client.delete(
        f"/admin/reviews/{review['id']}",
        headers=admin_auth["headers"],
    )
    assert deleted.status_code == 204


def test_review_moderation_admin_guards(
    client, customer_auth, product, monkeypatch
):
    monkeypatch.setattr(
        settings, "review_moderation_enabled", True
    )
    created = _review(
        client, customer_auth["headers"], product["id"]
    )
    assert created.status_code == 201

    anonymous = client.get("/admin/reviews")
    assert anonymous.status_code == 401

    forbidden = client.get(
        "/admin/reviews",
        headers=customer_auth["headers"],
    )
    assert forbidden.status_code == 403

    forbidden_update = client.patch(
        f"/admin/reviews/{created.json()['id']}",
        headers=customer_auth["headers"],
        json={"status": "published"},
    )
    assert forbidden_update.status_code == 403


def test_review_moderation_defaults_to_published(
    client, customer_auth, product
):
    created = _review(
        client, customer_auth["headers"], product["id"]
    )
    assert created.status_code == 201
    assert created.json()["status"] == "published"
