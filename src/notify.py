"""notify.py — email the owner via Gmail SMTP (App Password). Never fatal."""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

import config as C
from .utils import get_logger

log = get_logger("notify")


def email_owner(subject: str, body: str) -> bool:
    if not (C.GMAIL_USER and C.GMAIL_APP_PASSWORD and C.OWNER_EMAIL):
        log.info("Email not configured — skipping notify: %s", subject)
        return False
    try:
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = C.GMAIL_USER
        msg["To"] = C.OWNER_EMAIL
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(C.GMAIL_USER, C.GMAIL_APP_PASSWORD)
            s.sendmail(C.GMAIL_USER, [C.OWNER_EMAIL], msg.as_string())
        log.info("Emailed owner: %s", subject)
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("email_owner failed (non-fatal): %s", e)
        return False
