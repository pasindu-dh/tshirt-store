from io import BytesIO

from PIL import Image


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (16, 16), (16, 32, 64)).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(client, headers, filename, content, content_type):
    return client.post(
        "/admin/uploads",
        headers=headers,
        files={"file": (filename, content, content_type)},
    )


def test_valid_image_is_validated_stored_and_served(
    client, admin_auth
):
    response = _upload(
        client,
        admin_auth["headers"],
        "shirt.png",
        _png_bytes(),
        "image/png",
    )
    assert response.status_code == 201, response.text
    url = response.json()["url"]
    assert url.startswith("/uploads/")
    assert url.endswith(".png")

    served = client.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/png")
    assert served.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_invalid_image_payloads_are_rejected(client, admin_auth):
    headers = admin_auth["headers"]

    disguised = _upload(
        client, headers, "fake.png", b"not really an image", "image/png"
    )
    assert disguised.status_code == 400

    wrong_type = _upload(
        client, headers, "notes.txt", b"hello", "text/plain"
    )
    assert wrong_type.status_code == 415

    empty = _upload(client, headers, "empty.png", b"", "image/png")
    assert empty.status_code == 400


def test_oversized_image_is_rejected(client, admin_auth):
    oversized = b"\x89PNG\r\n\x1a\n" + b"0" * (5 * 1024 * 1024)
    response = _upload(
        client,
        admin_auth["headers"],
        "huge.png",
        oversized,
        "image/png",
    )
    assert response.status_code == 413


def test_upload_requires_admin(client, customer_auth):
    anonymous = _upload(
        client, {}, "shirt.png", _png_bytes(), "image/png"
    )
    customer = _upload(
        client,
        customer_auth["headers"],
        "shirt.png",
        _png_bytes(),
        "image/png",
    )

    assert anonymous.status_code == 401
    assert customer.status_code == 403
