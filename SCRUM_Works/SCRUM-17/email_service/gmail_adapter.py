"""SCRUM-17 | Level 1 (No Quantum Security): plain Gmail send/receive baseline.

Ticket: SCRUM-17
Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
"""
import base64
import mimetypes
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from typing import List, Optional

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


@dataclass
class Attachment:
    filename: str
    content_type: str
    data: bytes = b""
    attachment_id: Optional[str] = None  # Gmail id, used to download lazily


@dataclass
class EmailMessage:
    message_id: str
    sender: str = ""
    to: str = ""
    subject: str = ""
    date: str = ""
    snippet: str = ""
    body: str = ""
    attachments: List[Attachment] = field(default_factory=list)


class EmailProvider(ABC):
    """Provider interface so Gmail can later be swapped (Yahoo, IMAP/SMTP)."""

    @abstractmethod
    def send_message(self, to: str, subject: str, body: str,
                     attachments: Optional[List[str]] = None) -> str: ...

    @abstractmethod
    def list_messages(self, max_results: int = 10,
                      query: str = "in:inbox") -> List[EmailMessage]: ...

    @abstractmethod
    def get_message(self, message_id: str) -> EmailMessage: ...


class GmailAdapter(EmailProvider):
    def __init__(self, credentials_file: str = "credentials.json",
                 token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None

    # ---- auth (OAuth 2.0, no password stored) ----
    def authenticate(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as f:
                f.write(creds.to_json())
        self.service = build("gmail", "v1", credentials=creds)
        return self

    # ---- send (Level 1: plain MIME, no encryption) ----
    @staticmethod
    def build_mime(to: str, subject: str, body: str,
                   attachments: Optional[List[str]] = None) -> MimeMessage:
        msg = MimeMessage()
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        for path in attachments or []:
            ctype, _ = mimetypes.guess_type(path)
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
            with open(path, "rb") as f:
                msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                                   filename=os.path.basename(path))
        return msg

    def send_message(self, to, subject, body, attachments=None) -> str:
        mime = self.build_mime(to, subject, body, attachments)
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        sent = self.service.users().messages().send(
            userId="me", body={"raw": raw}).execute()
        return sent["id"]

    # ---- receive / inbox fetch ----
    def list_messages(self, max_results=10, query="in:inbox") -> List[EmailMessage]:
        resp = self.service.users().messages().list(
            userId="me", maxResults=max_results, q=query).execute()
        return [self.get_message(m["id"]) for m in resp.get("messages", [])]

    def get_message(self, message_id: str) -> EmailMessage:
        raw = self.service.users().messages().get(
            userId="me", id=message_id, format="full").execute()
        return self.parse_message(raw)

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        att = self.service.users().messages().attachments().get(
            userId="me", messageId=message_id, id=attachment_id).execute()
        return base64.urlsafe_b64decode(att["data"])

    # ---- parsing (pure function, testable without Gmail) ----
    @staticmethod
    def parse_message(raw: dict) -> EmailMessage:
        payload = raw.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        msg = EmailMessage(
            message_id=raw["id"],
            sender=headers.get("from", ""),
            to=headers.get("to", ""),
            subject=headers.get("subject", ""),
            date=headers.get("date", ""),
            snippet=raw.get("snippet", ""),
        )

        def walk(part):
            filename = part.get("filename")
            body = part.get("body", {})
            if filename:
                msg.attachments.append(Attachment(
                    filename=filename,
                    content_type=part.get("mimeType", "application/octet-stream"),
                    attachment_id=body.get("attachmentId")))
            elif part.get("mimeType") == "text/plain" and body.get("data") and not msg.body:
                msg.body = base64.urlsafe_b64decode(body["data"]).decode(
                    "utf-8", errors="replace")
            for sub in part.get("parts", []):
                walk(sub)

        walk(payload)
        return msg
