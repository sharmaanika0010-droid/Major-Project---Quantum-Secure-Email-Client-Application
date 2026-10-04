"""IMAP client for QuMail — connects to Gmail/Yahoo and fetches inbox headers.

SCRUM-16 (Day 3): login + fetch inbox list.
SCRUM-24 (Day 6): fetch full message (body + attachments) for rendering/preview.
"""
from __future__ import annotations

import email
import imaplib
from dataclasses import dataclass
from email.header import decode_header
from typing import List, Optional
import html as _html
import re

# Provider → (IMAP host, SMTP host). SMTP used later (Day 5).
PROVIDERS = {
    "Gmail": ("imap.gmail.com", "smtp.gmail.com"),
    "Yahoo": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com"),
}


# Custom headers written by QuMail when sending encrypted mail (see docs/uml/sequence_send_v1.md)
HDR_LEVEL = "X-QuMail-Level"
HDR_KEYID = "X-QuMail-KeyID"


@dataclass
class EmailSummary:
    uid: str
    sender: str
    subject: str
    date: str
    level: int = 1          # 1 = plain, 2/3/4 = encrypted by QuMail
    has_attachments: bool = False


@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes

    @property
    def size_kb(self) -> float:
        return round(len(self.data) / 1024, 1)


@dataclass
class EmailMessage:
    uid: str
    sender: str
    to: str
    subject: str
    date: str
    body: str                 # plain text (HTML stripped if no text part)
    attachments: List[Attachment]
    level: int = 1
    key_id: Optional[str] = None

    @property
    def is_encrypted(self) -> bool:
        return self.level > 1


class IMAPError(Exception):
    """Raised when login or fetch fails (shown to the user by the GUI)."""


def _decode(value: str | None) -> str:
    """Decode RFC2047 encoded headers like =?UTF-8?B?...?= into plain text."""
    if not value:
        return ""
    parts = []
    for text, charset in decode_header(value):
        if isinstance(text, bytes):
            parts.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(text)
    return "".join(parts)


def _html_to_text(markup: str) -> str:
    """Very small HTML → text fallback (no external deps)."""
    markup = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", markup)
    text = re.sub(r"<[^>]+>", "", markup)
    text = _html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _level_of(msg) -> int:
    try:
        return int((msg.get(HDR_LEVEL) or "1").strip())
    except ValueError:
        return 1


class IMAPClient:
    def __init__(self, provider: str, address: str, app_password: str):
        if provider not in PROVIDERS:
            raise IMAPError(f"Unknown provider: {provider}")
        self.host = PROVIDERS[provider][0]
        self.address = address
        self._password = app_password
        self._conn: imaplib.IMAP4_SSL | None = None

    # -- connection -----------------------------------------------------
    def connect(self) -> None:
        try:
            self._conn = imaplib.IMAP4_SSL(self.host, 993)
            self._conn.login(self.address, self._password)
        except imaplib.IMAP4.error as exc:
            raise IMAPError("Login failed — check email / app password") from exc
        except OSError as exc:
            raise IMAPError(f"Cannot reach {self.host}: {exc}") from exc

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.logout()
            finally:
                self._conn = None

    # -- inbox ----------------------------------------------------------
    def fetch_inbox(self, limit: int = 20) -> List[EmailSummary]:
        """Return the newest `limit` messages (headers only, fast)."""
        if self._conn is None:
            raise IMAPError("Not connected")
        status, _ = self._conn.select("INBOX", readonly=True)
        if status != "OK":
            raise IMAPError("Cannot open INBOX")

        status, data = self._conn.uid("search", None, "ALL")
        if status != "OK":
            raise IMAPError("Search failed")
        uids = data[0].split()
        newest = uids[-limit:][::-1]  # newest first

        result: List[EmailSummary] = []
        for uid in newest:
            status, msg_data = self._conn.uid(
                "fetch", uid, f"(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE CONTENT-TYPE {HDR_LEVEL})])"
            )
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            result.append(
                EmailSummary(
                    uid=uid.decode(),
                    sender=_decode(msg.get("From")),
                    subject=_decode(msg.get("Subject")) or "(no subject)",
                    date=msg.get("Date", ""),
                    level=_level_of(msg),
                    has_attachments="multipart/mixed" in (msg.get("Content-Type") or "").lower(),
                )
            )
        return result

    # -- single message (Day 6) ----------------------------------------
    def fetch_message(self, uid: str) -> EmailMessage:
        """Download one full message: headers, text body and attachments."""
        if self._conn is None:
            raise IMAPError("Not connected")
        status, data = self._conn.uid("fetch", uid.encode(), "(BODY.PEEK[])")
        if status != "OK" or not data or data[0] is None:
            raise IMAPError(f"Cannot fetch message {uid}")
        msg = email.message_from_bytes(data[0][1])

        text_part, html_part = None, None
        attachments: List[Attachment] = []
        for part in msg.walk():
            if part.is_multipart():
                continue
            ctype = part.get_content_type()
            disp = (part.get("Content-Disposition") or "").lower()
            filename = part.get_filename()
            if filename or "attachment" in disp:
                payload = part.get_payload(decode=True) or b""
                attachments.append(Attachment(_decode(filename) or "attachment.bin", ctype, payload))
            elif ctype == "text/plain" and text_part is None:
                text_part = part
            elif ctype == "text/html" and html_part is None:
                html_part = part

        def _text(part) -> str:
            raw = part.get_payload(decode=True) or b""
            return raw.decode(part.get_content_charset() or "utf-8", errors="replace")

        if text_part is not None:
            body = _text(text_part)
        elif html_part is not None:
            body = _html_to_text(_text(html_part))
        else:
            body = "(no text body)"

        return EmailMessage(
            uid=uid,
            sender=_decode(msg.get("From")),
            to=_decode(msg.get("To")),
            subject=_decode(msg.get("Subject")) or "(no subject)",
            date=msg.get("Date", ""),
            body=body,
            attachments=attachments,
            level=_level_of(msg),
            key_id=(msg.get(HDR_KEYID) or None),
        )


if __name__ == "__main__":  # quick manual test: python -m qumail.email.imap_client
    import getpass
    import sys

    addr = input("Email: ")
    pwd = getpass.getpass("App password: ")
    prov = "Yahoo" if "yahoo" in addr.lower() else "Gmail"
    c = IMAPClient(prov, addr, pwd)
    try:
        c.connect()
        for m in c.fetch_inbox(10):
            print(f"{m.date[:22]:22} | {m.sender[:30]:30} | {m.subject[:50]}")
    except IMAPError as e:
        print("ERROR:", e)
        sys.exit(1)
    finally:
        c.close()
