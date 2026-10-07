"""Outbound email (Feature 002 BE-010/BE-011): a real SMTP send via stdlib smtplib. This
remains the single seam tests patch to capture what would have been sent."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from src.infrastructure.config import settings

logger = logging.getLogger("localfix.email")


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    # The reset_link embeds a single-use credential token - never log it (FR-018/FR-026's
    # no-secrets-in-logs principle applies here too).
    message = EmailMessage()
    message["Subject"] = "Reset your LocalFix password"
    message["From"] = settings.smtp_from_address
    message["To"] = to_email
    message.set_content(f"Use the link below to reset your password:\n\n{reset_link}")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)

    logger.info("Password reset email dispatched to %s", to_email)
