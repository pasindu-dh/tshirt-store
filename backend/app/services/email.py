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
) -> bool:
    return _send_email(
        to_email,
        f"FURZY order #{order_id} confirmed",
        (
            f"Hi {contact_name},\n\n"
            f"Thank you for your order #{order_id}. "
            f"Your total is LKR {total}.\n\n"
            "We will update you when your order is confirmed and shipped.\n\n"
            "FURZY"
        ),
    )


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
