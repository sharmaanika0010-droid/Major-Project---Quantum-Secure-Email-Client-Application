
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_email(to_email, subject, body, attachments=None):
    """
    Send an email with optional file attachments.
    SMTP credentials must be set in environment variables.
    """

    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_user or not smtp_password:
        raise RuntimeError(
            "Set SMTP_USER and SMTP_PASSWORD environment variables first."
        )

    if not to_email or "@" not in to_email:
        raise ValueError("Please provide a valid recipient email address.")

    message = EmailMessage()
    message["From"] = smtp_user
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    for file_path in attachments or []:
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"Attachment not found: {path}")

        message.add_attachment(
            path.read_bytes(),
            maintype="application",
            subtype="octet-stream",
            filename=path.name,
        )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)

    return True
