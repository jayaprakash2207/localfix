"""Outbound email. No real SMTP/provider is configured for this feature (out of spec scope);
this is the single seam tests patch to capture what would have been sent."""

from __future__ import annotations

import logging

logger = logging.getLogger("localfix.email")


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    # The reset_link embeds a single-use credential token - never log it (FR-018/FR-026's
    # no-secrets-in-logs principle applies here too, even though this stub has no real
    # email provider to hand it to instead).
    logger.info("Password reset email dispatched to %s", to_email)
