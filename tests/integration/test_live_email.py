"""Optional LIVE round-trip through a real mailbox (Gmail/Yahoo). Skipped unless credentials
are provided — run locally before a demo:

    set QUMAIL_TEST_EMAIL=qumailtest71@gmail.com
    set QUMAIL_TEST_PASSWORD=<app password>
    python -m pytest tests/integration/test_live_email.py -q
"""
from __future__ import annotations

import os
import time
import uuid

import pytest

from qumail.crypto import pipeline
from qumail.email.imap_client import IMAPClient
from qumail.email.smtp_client import SMTPClient

pytestmark = pytest.mark.live

EMAIL = os.environ.get("QUMAIL_TEST_EMAIL")
PASSWORD = os.environ.get("QUMAIL_TEST_PASSWORD")


@pytest.mark.skipif(not (EMAIL and PASSWORD), reason="set QUMAIL_TEST_EMAIL / QUMAIL_TEST_PASSWORD")
def test_level3_round_trip_via_real_mailbox(tmp_path, km):
    f = tmp_path / "otp_test.txt"
    f.write_text("integration attachment " + uuid.uuid4().hex)
    subject = f"QuMail L3 integration {uuid.uuid4().hex[:8]}"
    prepared, wire = pipeline.prepare(3, "live body", [str(f)], km)

    smtp = SMTPClient(EMAIL, PASSWORD)
    smtp.connect()
    smtp.send(to=EMAIL, subject=subject, body=prepared.body, attachments=wire, headers=prepared.headers())
    smtp.close()

    imap = IMAPClient(EMAIL, PASSWORD)
    imap.connect()
    found = None
    for _ in range(12):                                            # poll up to ~1 min
        for item in imap.fetch_inbox(limit=10):
            if item.subject == subject:
                found = imap.fetch_message(item.uid)
                break
        if found:
            break
        time.sleep(5)
    imap.close()
    assert found, "mail did not arrive"
    pipeline.open_message(found, km)
    assert found.body.startswith("live body")                      # provider may append a footer
    assert found.attachments[0].data == f.read_bytes()
