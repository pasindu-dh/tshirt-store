import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from app.config import settings


def _request_json(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict | None = None,
    timeout: float = 10,
):
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers or {},
        method=method,
    )

    try:
        with urllib.request.urlopen(
            request, timeout=timeout
        ) as response:
            body = response.read().decode("utf-8")
            return response.status, (
                json.loads(body) if body else None
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")

        try:
            payload = json.loads(body) if body else None
        except json.JSONDecodeError:
            payload = None

        return exc.code, payload


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def run_smoke_checks(
    base_url: str,
    *,
    skip_admin: bool = False,
    timeout: float = 10,
) -> bool:
    passed = True

    def check(name: str, func) -> None:
        nonlocal passed

        try:
            detail = func()
        except Exception as exc:
            passed = False
            print(f"[FAIL] {name}: {exc}")
        else:
            suffix = f" - {detail}" if detail else ""
            print(f"[PASS] {name}{suffix}")

    def expect_json(
        path: str,
        *,
        expected_status: int = 200,
        predicate=None,
    ):
        status, payload = _request_json(
            _url(base_url, path), timeout=timeout
        )

        if status != expected_status:
            raise RuntimeError(f"HTTP {status}")

        if predicate is not None and not predicate(payload):
            raise RuntimeError("unexpected response body")

        return payload

    check(
        "liveness",
        lambda: (
            expect_json("/health/live")
            .get("status", "")
            or "missing status"
        ),
    )
    check(
        "readiness",
        lambda: (
            expect_json(
                "/health/ready",
                predicate=lambda data: data.get("status")
                == "ready",
            ).get("status")
        ),
    )
    check(
        "catalog",
        lambda: (
            f"{len(expect_json('/products', predicate=lambda data: isinstance(data, list)))} product(s)"
        ),
    )
    check(
        "payment config",
        lambda: (
            expect_json("/payments/config")
            .get("provider", "ok")
        ),
    )
    check(
        "account config",
        lambda: (
            "email_verification_required"
            in expect_json(
                "/auth/config",
                predicate=lambda data: (
                    "password_reset_available" in data
                ),
            )
            and "ok"
        ),
    )

    email = (
        os.environ.get("SMOKE_ADMIN_EMAIL", "").strip()
        or settings.admin_email.strip()
    )
    password = (
        os.environ.get("SMOKE_ADMIN_PASSWORD", "")
        or settings.admin_password
    )

    if skip_admin or not email or not password:
        print(
            "[SKIP] admin authentication "
            "(no smoke/admin credentials configured)"
        )
        return passed

    def admin_login():
        body = urllib.parse.urlencode(
            {"username": email, "password": password}
        ).encode("utf-8")
        status, payload = _request_json(
            _url(base_url, "/auth/login"),
            method="POST",
            data=body,
            headers={
                "Content-Type": (
                    "application/x-www-form-urlencoded"
                )
            },
            timeout=timeout,
        )

        if status != 200:
            raise RuntimeError(f"HTTP {status}")

        token = payload.get("access_token") if payload else None

        if not token:
            raise RuntimeError("missing access token")

        return {
            "Authorization": f"Bearer {token}"
        }

    auth_headers: dict = {}

    def login_check():
        auth_headers.update(admin_login())
        return "token issued"

    check("admin login", login_check)

    def authed_json(path: str):
        status, payload = _request_json(
            _url(base_url, path),
            headers=auth_headers,
            timeout=timeout,
        )

        if status != 200:
            raise RuntimeError(f"HTTP {status}")

        return payload

    if auth_headers:
        def identity():
            role = authed_json("/auth/me").get("role")

            if role != "admin":
                raise RuntimeError(
                    f"expected admin role, got {role!r}"
                )

            return "admin"

        check("admin identity", identity)
        check(
            "admin stats",
            lambda: (
                authed_json("/admin/stats") is not None
                and "ok"
            ),
        )
        check(
            "admin reviews",
            lambda: (
                isinstance(
                    authed_json("/admin/reviews?limit=1"),
                    list,
                )
                and "ok"
            ),
        )

    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run FURZY API launch smoke checks against a "
            "running backend."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get(
            "SMOKE_BASE_URL",
            settings.backend_public_url,
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10,
    )
    parser.add_argument(
        "--skip-admin",
        action="store_true",
    )
    args = parser.parse_args(argv)

    print(f"Smoke target: {args.base_url}")
    ok = run_smoke_checks(
        args.base_url,
        skip_admin=args.skip_admin,
        timeout=args.timeout,
    )
    print("Smoke result:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
