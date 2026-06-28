# src/lib/alert.py
from __future__ import annotations

import os
from typing import Any

import structlog
from jinja2 import Environment, FileSystemLoader

log = structlog.get_logger()

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def _get_jinja_env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def send_alert(
    template_name: str,
    subject: str,
    to_email: str,
    from_email: str,
    sendgrid_api_key: str = "",
    **template_vars: Any,
) -> None:
    """Send an alert email via SendGrid."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    env = _get_jinja_env()
    template = env.get_template(template_name)
    body = template.render(**template_vars)

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )

    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        log.info("alert.sent", to=to_email, subject=subject, status_code=response.status_code)
    except Exception as e:
        log.error("alert.failed", error=str(e))
