import base64
import json
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from threading import Lock
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from app.config import settings

logger = logging.getLogger("furzy.payhere_api")

SANDBOX_BASE = "https://sandbox.payhere.lk"
LIVE_BASE = "https://www.payhere.lk"
TOKEN_PATH = "/merchant/v1/oauth/token"
SEARCH_PATH = "/merchant/v1/payment/search"
REFUND_PATH = "/merchant/v1/payment/refund"

_token_lock = Lock()
_token_cache: str | None = None
_token_expires_at = 0.0


class PayHereApiError(Exception):
    pass


@dataclass
class ProviderPayment:
    payment_id: str
    order_id: str
    status: str
    amount: Decimal
    currency: str


@dataclass
class ProviderRefund:
    refund_id: str
    status: str


def _is_mock() -> bool:
    return (
        settings.normalized_payment_provider == "mock"
        and settings.payment_mock_enabled
        and not settings.is_production
    )


def _base_url() -> str:
    return SANDBOX_BASE if settings.payhere_sandbox else LIVE_BASE


def _authorization_code() -> str:
    raw = (
        f"{settings.payhere_api_app_id}:"
        f"{settings.payhere_api_app_secret}"
    )
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def _clear_token() -> None:
    global _token_cache, _token_expires_at

    with _token_lock:
        _token_cache = None
        _token_expires_at = 0.0


def _get_access_token() -> str:
    global _token_cache, _token_expires_at

    if _is_mock():
        return "mock-access-token"

    if not settings.payhere_api_enabled:
        raise PayHereApiError(
            "PayHere Merchant API credentials are not configured."
        )

    with _token_lock:
        if (
            _token_cache is not None
            and monotonic() < _token_expires_at
        ):
            return _token_cache

        request = Request(
            f"{_base_url()}{TOKEN_PATH}",
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {_authorization_code()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=settings.payhere_api_timeout_seconds,
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise PayHereApiError(
                "PayHere Merchant API authentication failed."
            ) from exc

        token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 0) or 0)

        if not token:
            raise PayHereApiError(
                "PayHere Merchant API authentication failed."
            )

        _token_cache = str(token)
        _token_expires_at = monotonic() + max(30, expires_in - 60)
        return _token_cache


def _request_json(
    method: str,
    path: str,
    *,
    query: dict[str, str] | None = None,
    body: dict | None = None,
) -> dict:
    url = f"{_base_url()}{path}"

    if query:
        url = f"{url}?{urlencode(query)}"

    data = None
    headers = {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }

    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(
            request,
            timeout=settings.payhere_api_timeout_seconds,
        ) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 401:
            _clear_token()
            raise PayHereApiError(
                "PayHere Merchant API access was denied."
            ) from exc

        raise PayHereApiError(
            "PayHere Merchant API request failed."
        ) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise PayHereApiError(
            "PayHere Merchant API request failed."
        ) from exc


def verify_credentials() -> None:
    """Acquire a Merchant API token to validate the configured key."""

    if _is_mock():
        return

    _get_access_token()


def lookup_payment(
    reference: str,
    *,
    expected_amount: int,
    currency: str,
) -> ProviderPayment:
    if _is_mock():
        return ProviderPayment(
            payment_id=f"mock-{reference}",
            order_id=reference,
            status="RECEIVED",
            amount=Decimal(expected_amount),
            currency=currency.strip().upper(),
        )

    if not settings.payhere_api_enabled:
        raise PayHereApiError(
            "PayHere Merchant API credentials are not configured."
        )

    payload = _request_json(
        "GET",
        SEARCH_PATH,
        query={"order_id": reference},
    )
    top_status = payload.get("status")

    if top_status == -1:
        raise PayHereApiError("No PayHere payment was found.")
    if top_status == -2:
        raise PayHereApiError(
            "PayHere Merchant API authentication failed."
        )
    if top_status != 1:
        raise PayHereApiError(
            "PayHere Merchant API returned an unexpected response."
        )

    entries = payload.get("data") or []
    match = next(
        (
            entry
            for entry in entries
            if str(entry.get("order_id")) == reference
        ),
        None,
    )

    if match is None:
        raise PayHereApiError("No PayHere payment was found.")

    amount_value = match.get("amount")

    if amount_value is None:
        amount_value = (match.get("amount_detail") or {}).get("gross")

    try:
        amount = Decimal(str(amount_value))
    except (InvalidOperation, TypeError) as exc:
        raise PayHereApiError(
            "PayHere returned an invalid payment amount."
        ) from exc

    return ProviderPayment(
        payment_id=str(match.get("payment_id") or ""),
        order_id=str(match.get("order_id") or ""),
        status=str(match.get("status") or "").strip().upper(),
        amount=amount,
        currency=str(match.get("currency") or "").strip().upper(),
    )


def refund_payment(
    payment_id: str,
    *,
    amount: int,
    description: str,
) -> ProviderRefund:
    if _is_mock():
        return ProviderRefund(
            refund_id=f"mock-refund-{uuid4().hex[:12].upper()}",
            status="refunded",
        )

    if not settings.payhere_api_enabled:
        raise PayHereApiError(
            "PayHere Merchant API credentials are not configured."
        )

    payload = _request_json(
        "POST",
        REFUND_PATH,
        body={
            "payment_id": payment_id,
            "description": description,
            "amount": f"{amount:.2f}",
        },
    )
    status = payload.get("status")

    if status == 1:
        return ProviderRefund(
            refund_id=str(payload.get("data") or ""),
            status="refunded",
        )
    if status == 0:
        return ProviderRefund(
            refund_id=str(payload.get("data") or ""),
            status="processing",
        )
    if status == -2:
        raise PayHereApiError(
            "PayHere Merchant API authentication failed."
        )

    raise PayHereApiError("PayHere refund request failed.")
