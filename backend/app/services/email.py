import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("furzy.email")


def _send_email(to_email: str, subject: str, body: str) -> bool:
    if (
        not settings.smtp_host
        or not settings.smtp_from_email
        or not to_email
    ):
        logger.info("Email skipped because SMTP is not configured.")
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=10,
        ) as server:
            if settings.smtp_use_tls:
                server.starttls()

            if settings.smtp_username:
                server.login(
                    settings.smtp_username,
                    settings.smtp_password,
                )

            server.send_message(message)

        return True
    except Exception:
        logger.exception("Could not send an order notification email.")
        return False


def send_order_confirmation(
    to_email: str,
    order_id: int,
    contact_name: str,
    total: int,
    payment_method: str,
    payment_status: str,
) -> bool:
    if payment_method == "online" and payment_status == "paid":
        subject = f"FURZY order #{order_id} confirmed and paid"
        body = (
            f"Hi {contact_name},\n\n"
            f"Your FURZY order #{order_id} is confirmed and paid. "
            f"Total: LKR {total}.\n\n"
            "We will notify you when it is shipped.\n\n"
            "FURZY"
        )
    elif payment_method == "online" and payment_status == "failed":
        subject = f"FURZY order #{order_id} received - payment failed"
        body = (
            f"Hi {contact_name},\n\n"
            f"Your FURZY order #{order_id} has been received, but "
            "the online payment did not succeed. The order remains "
            f"pending. Total: LKR {total}.\n\n"
            "You can retry payment from your order page.\n\n"
            "FURZY"
        )
    elif payment_method == "online":
        subject = (
            f"FURZY order #{order_id} received - payment pending"
        )
        body = (
            f"Hi {contact_name},\n\n"
            f"We received your FURZY order #{order_id}. "
            "Your online payment has not been confirmed yet. "
            f"Total: LKR {total}.\n\n"
            "Complete payment from your order page. We will send a "
            "separate confirmation once payment is verified.\n\n"
            "FURZY"
        )
    else:
        subject = f"FURZY order #{order_id} confirmed"
        body = (
            f"Hi {contact_name},\n\n"
            f"Thank you for your order #{order_id}. "
            f"Your total is LKR {total} and payment is due on "
            "delivery (Cash on Delivery).\n\n"
            "We will update you when your order is shipped.\n\n"
            "FURZY"
        )

    return _send_email(to_email, subject, body)


def send_payment_confirmation(
    to_email: str,
    order_id: int,
    contact_name: str,
    total: int,
    reference: str,
) -> bool:
    return _send_email(
        to_email,
        f"Payment received for FURZY order #{order_id}",
        (
            f"Hi {contact_name},\n\n"
            f"We have verified your payment of LKR {total} for "
            f"FURZY order #{order_id}.\n"
            f"Reference: {reference}\n\n"
            "Thank you.\n\n"
            "FURZY"
        ),
    )


def send_return_status_update(
    to_email: str,
    order_id: int,
    return_id: int,
    status: str,
    note: str = "",
) -> bool:
    subjects = {
        "requested": "Return request received",
        "approved": "Return request approved",
        "rejected": "Return request rejected",
        "completed": "Return completed",
        "cancelled": "Return request cancelled",
    }
    subject = (
        f"FURZY return #{return_id} for order #{order_id}: "
        f"{subjects.get(status, status)}"
    )
    body = (
        f"Your return request #{return_id} for FURZY order "
        f"#{order_id} is now: {status}.\n\n"
    )

    if note:
        body += f"Note: {note}\n\n"

    body += "FURZY"
    return _send_email(to_email, subject, body)


def send_order_status_update(
    to_email: str,
    order_id: int,
    status: str,
) -> bool:
    return _send_email(
        to_email,
        f"FURZY order #{order_id} is {status}",
        (
            f"Your FURZY order #{order_id} has been updated to: "
            f"{status}.\n\n"
            "You can review your order history from your account.\n\n"
            "FURZY"
        ),
    )
