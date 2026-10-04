"""IMAP client for QuMail — connects to Gmail/Yahoo and fetches inbox headers.

SCRUM-16 (Day 3): login + fetch inbox list.
"""
from __future__ import annotations

import email
import imaplib
from dataclasses import dataclass
from email.header import decode_header
from typing import List

# Provider → (IMAP host, SMTP host). SMTP used later (Day 5).
PROVIDERS = {
    "Gmail": ("imap.gmail.com", "smtp.gmail.com"),
    "Yahoo": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com"),
}


@dataclass
class EmailSummary:
    uid: str
    sender: str
    subject: str
    date: str


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
                "fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
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
                )
            )
        return result


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
