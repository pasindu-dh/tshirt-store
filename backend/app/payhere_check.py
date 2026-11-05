"""PayHere sandbox/live configuration check.

Examples:

    PAYMENT_PROVIDER=payhere PAYHERE_MERCHANT_ID=... \
    PAYHERE_MERCHANT_SECRET=... PAYHERE_API_APP_ID=... \
    PAYHERE_API_APP_SECRET=... PAYHERE_SANDBOX=true \
    python -m app.payhere_check --check-api

    python -m app.payhere_check --reference FURZY-ORDER-123 \
      --amount 2450 --check-api

The command never prints merchant secrets or API keys.
"""

import argparse
import sys
from dataclasses import dataclass

from app.config import Settings, settings
from app.services import payhere_api


@dataclass
class Check:
    status: str
    name: str
    detail: str = ""


def config_checks(config: Settings) -> list[Check]:
    checks: list[Check] = []

    def add(ok: bool, name: str, detail: str = "") -> None:
        checks.append(
            Check("PASS" if ok else "FAIL", name, detail)
        )

    add(
        config.normalized_payment_provider == "payhere",
        "PAYMENT_PROVIDER",
        "must be payhere to use hosted checkout",
    )
    add(
        bool(config.payhere_merchant_id.strip())
        and bool(config.payhere_merchant_secret.strip()),
        "PAYHERE_CHECKOUT_CREDENTIALS",
        "merchant ID and secret are required for checkout/notifications",
    )
    add(
        not config.payment_mock_enabled,
        "PAYMENT_MOCK_ENABLED",
        "mock completion must be disabled for sandbox/live testing",
    )
    checks.append(
        Check(
            "PASS" if config.payhere_sandbox else "WARN",
            "PAYHERE_SANDBOX",
            (
                "sandbox mode"
                if config.payhere_sandbox
                else "live mode; use sandbox credentials first"
            ),
        )
    )
    checks.append(
        Check(
            "PASS" if config.payhere_api_enabled else "WARN",
            "PAYHERE_API_CREDENTIALS",
            (
                "Merchant API retrieval/refunds available"
                if config.payhere_api_enabled
                else "Merchant API not configured; use manual "
                "reconciliation/refund records"
            ),
        )
    )

    notify_url = (
        f"{config.backend_public_url.rstrip('/')}"
        "/payments/payhere/notify"
    )
    checks.append(
        Check(
            (
                "PASS"
                if notify_url.startswith("https://")
                else "WARN"
            ),
            "NOTIFY_URL",
            f"{notify_url} (must be publicly reachable over HTTPS "
            "for sandbox/live notifications)",
        )
    )

    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate PayHere configuration and optionally verify "
            "Merchant API access."
        )
    )
    parser.add_argument(
        "--check-api",
        action="store_true",
        help="acquire a Merchant API token to validate the key",
    )
    parser.add_argument(
        "--reference",
        default="",
        help="merchant order reference to retrieve",
    )
    parser.add_argument(
        "--amount",
        type=int,
        default=0,
        help="expected amount for the reference",
    )
    args = parser.parse_args(argv)

    checks = config_checks(settings)
    failures = sum(
        1 for check in checks if check.status == "FAIL"
    )

    for check in checks:
        suffix = f" - {check.detail}" if check.detail else ""
        print(f"[{check.status}] {check.name}{suffix}")

    if args.check_api:
        if not settings.payhere_api_enabled:
            print(
                "[SKIP] Merchant API check "
                "(PAYHERE_API_APP_ID/SECRET not configured)"
            )
        else:
            try:
                payhere_api.verify_credentials()
            except payhere_api.PayHereApiError as exc:
                failures += 1
                print(f"[FAIL] Merchant API authentication - {exc}")
            else:
                print("[PASS] Merchant API authentication")

    if args.reference:
        if not settings.payhere_api_enabled:
            print(
                "[SKIP] payment retrieval "
                "(Merchant API credentials not configured)"
            )
        else:
            try:
                payment = payhere_api.lookup_payment(
                    args.reference,
                    expected_amount=args.amount,
                    currency=settings.payment_currency,
                )
            except payhere_api.PayHereApiError as exc:
                failures += 1
                print(f"[FAIL] payment retrieval - {exc}")
            else:
                print(
                    "[PASS] payment retrieval - "
                    f"status={payment.status} "
                    f"amount={payment.amount} "
                    f"currency={payment.currency}"
                )

                if (
                    args.amount
                    and int(payment.amount) != args.amount
                ):
                    failures += 1
                    print(
                        "[FAIL] payment amount does not match the "
                        "expected amount"
                    )

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
