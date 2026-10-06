"""SMTP sender for QuMail (Gmail / Yahoo) — SCRUM-28 (Day 7).

Uses the same app password as IMAP. Attachments and QuMail headers supported.
"""
from __future__ import annotations

import mimetypes
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Dict, Iterable, Optional

from qumail.email.imap_client import PROVIDERS


class SMTPError(Exception):
    """Raised when sending fails (shown to the user by the GUI)."""


class SMTPClient:
    def __init__(self, provider: str, address: str, app_password: str):
        if provider not in PROVIDERS:
            raise SMTPError(f"Unknown provider: {provider}")
        self.host = PROVIDERS[provider][1]
        self.address = address
        self._password = app_password

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        headers: Optional[Dict[str, str]] = None,
        attachments: Iterable[str] = (),
    ) -> str:
        """Send one message; returns the Message-ID."""
        msg = EmailMessage()
        msg["From"] = self.address
        msg["To"] = to
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="qumail.local")
        for k, v in (headers or {}).items():
            msg[k] = v
        msg.set_content(body)

        for path in attachments:
            p = Path(path)
            ctype, _ = mimetypes.guess_type(p.name)
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
            msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name)

        try:
            with smtplib.SMTP_SSL(self.host, 465, context=ssl.create_default_context(), timeout=30) as s:
                s.login(self.address, self._password)
                s.send_message(msg)
        except smtplib.SMTPAuthenticationError as exc:
            raise SMTPError("SMTP login failed — check email / app password") from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise SMTPError(f"Send failed: {exc}") from exc
        return msg["Message-ID"]
