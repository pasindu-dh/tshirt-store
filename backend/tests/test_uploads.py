from io import BytesIO
from pathlib import Path

from PIL import Image
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal, engine
from app.models import UploadedImage


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

    filename = url.rsplit("/", 1)[1]
    assert not (Path(settings.uploads_dir) / filename).exists()

    with SessionLocal() as db:
        stored = db.scalar(
            select(UploadedImage).where(
                UploadedImage.filename == filename
            )
        )
        assert stored is not None
        assert stored.content_type == "image/png"
        assert stored.data.startswith(b"\x89PNG\r\n\x1a\n")

    served = client.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/png")
    assert served.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert "immutable" in served.headers["cache-control"]


def test_upload_falls_back_when_database_table_is_missing(
    client, admin_auth
):
    UploadedImage.__table__.drop(bind=engine)

    response = _upload(
        client,
        admin_auth["headers"],
        "fallback.png",
        _png_bytes(),
        "image/png",
    )
    assert response.status_code == 201, response.text
    url = response.json()["url"]
    filename = url.rsplit("/", 1)[1]
    assert (Path(settings.uploads_dir) / filename).exists()

    served = client.get(url)
    assert served.status_code == 200
    assert served.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_production_does_not_fall_back_to_ephemeral_storage(
    client, admin_auth, monkeypatch
):
    UploadedImage.__table__.drop(bind=engine)
    monkeypatch.setattr(settings, "app_env", "production")

    response = _upload(
        client,
        admin_auth["headers"],
        "production.png",
        _png_bytes(),
        "image/png",
    )

    assert response.status_code == 503
    assert "migrations" in response.json()["detail"].lower()
    assert not (
        Path(settings.uploads_dir) / "production.png"
    ).exists()


def test_legacy_filesystem_upload_is_still_served(
    client,
):
    filename = "legacy-image.png"
    Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
    (Path(settings.uploads_dir) / filename).write_bytes(
        _png_bytes()
    )

    served = client.get(f"/uploads/{filename}")
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/png")


def test_upload_serving_rejects_unsafe_filenames(client):
    assert client.get("/uploads/notes.txt").status_code == 404
    assert (
        client.get("/uploads/%2e%2e%2fstore.db").status_code
        == 404
    )
    assert client.get("/uploads/missing.png").status_code == 404


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
