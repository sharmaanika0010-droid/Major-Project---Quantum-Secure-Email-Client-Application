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
from typing import Dict, Iterable, Optional, Tuple, Union

from qumail.config import get_settings
from qumail.email.imap_client import PROVIDERS


class SMTPError(Exception):
    """Raised when sending fails (shown to the user by the GUI)."""


class SMTPClient:
    def __init__(self, provider: str, address: str, app_password: str,
                 timeout: Optional[int] = None, port: Optional[int] = None):
        if provider not in PROVIDERS:
            raise SMTPError(f"Unknown provider: {provider}")
        self.host = PROVIDERS[provider][1]
        self.address = address.strip()
        self._password = "".join(app_password.split())   # SCRUM-63: tolerate pasted spaces
        cfg = get_settings()
        self.timeout = timeout or cfg.smtp_timeout
        self.port = port or cfg.smtp_port

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        headers: Optional[Dict[str, str]] = None,
        attachments: Iterable[Union[str, Tuple[str, bytes]]] = (),
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

        for item in attachments:
            if isinstance(item, tuple):          # (filename, bytes) — already-encrypted blobs
                name, data = item
            else:                                # path on disk
                p = Path(item)
                name, data = p.name, p.read_bytes()
            ctype, _ = mimetypes.guess_type(name)
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)

        try:
            with smtplib.SMTP_SSL(self.host, self.port, context=ssl.create_default_context(), timeout=self.timeout) as s:
                s.login(self.address, self._password)
                s.send_message(msg)
        except smtplib.SMTPAuthenticationError as exc:
            detail = exc.smtp_error.decode(errors="replace") if isinstance(exc.smtp_error, bytes) else str(exc.smtp_error)
            raise SMTPError(f"SMTP login failed: {detail}") from exc
        except (smtplib.SMTPException, OSError) as exc:
            raise SMTPError(f"Send failed: {exc}") from exc
        return msg["Message-ID"]
