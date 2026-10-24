import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from src.email.smtp_sender import send_email


class TestSmtpSender(unittest.TestCase):

    @patch("src.email.smtp_sender.smtplib.SMTP")
    @patch.dict("os.environ", {
        "SMTP_USER": "sender@example.com",
        "SMTP_PASSWORD": "test-password",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
    })
    def test_send_email(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value

        result = send_email(
            "receiver@example.com",
            "Test Subject",
            "Test message"
        )

        self.assertTrue(result)
        server.starttls.assert_called_once()
        server.login.assert_called_once()
        server.send_message.assert_called_once()

    @patch("src.email.smtp_sender.smtplib.SMTP")
    @patch.dict("os.environ", {
        "SMTP_USER": "sender@example.com",
        "SMTP_PASSWORD": "test-password",
        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
    })
    def test_send_email_with_attachment(self, mock_smtp):
        server = mock_smtp.return_value.__enter__.return_value

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "sample.txt"
            file_path.write_text("Test attachment", encoding="utf-8")

            result = send_email(
                "receiver@example.com",
                "Attachment Test",
                "Please find the attachment.",
                attachments=[str(file_path)],
            )

        self.assertTrue(result)

        sent_message = server.send_message.call_args.args[0]

        self.assertEqual(
            len(list(sent_message.iter_attachments())),
            1
        )


if __name__ == "__main__":
    unittest.main()