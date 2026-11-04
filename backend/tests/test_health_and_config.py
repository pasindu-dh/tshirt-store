import pytest

from app.config import Settings, validate_runtime_security
from app.routers import health


def test_health_liveness_and_readiness(client):
    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks"] == {
        "database": "ok",
        "uploads": "ok",
    }


def test_readiness_reports_upload_failure(
    client, tmp_path, monkeypatch
):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("blocked", encoding="utf-8")
    monkeypatch.setattr(
        health.settings, "uploads_dir", str(blocker)
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unready"
    assert response.json()["checks"]["database"] == "ok"
    assert response.json()["checks"]["uploads"] == "error"


def _production_settings(**overrides):
    values = {
        "app_env": "production",
        "jwt_secret": "x" * 48,
        "frontend_origins": "https://shop.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_security_validation():
    validate_runtime_security(_production_settings())

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_runtime_security(
            _production_settings(jwt_secret="short")
        )

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_runtime_security(
            _production_settings(
                jwt_secret="dev-secret-change-me"
            )
        )

    with pytest.raises(
        RuntimeError, match="FRONTEND_ORIGINS"
    ):
        validate_runtime_security(
            _production_settings(frontend_origins="*")
        )

    validate_runtime_security(
        Settings(
            _env_file=None,
            app_env="development",
            jwt_secret="short",
            frontend_origins="*",
        )
    )
