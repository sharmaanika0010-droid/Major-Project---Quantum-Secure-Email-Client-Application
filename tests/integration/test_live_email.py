"""LIVE regression matrix through a real mailbox (SCRUM-69): every level × attachment, Gmail or Yahoo.

Skipped unless credentials are provided. Run locally before a demo, with the KM simulator running:

    set QUMAIL_TEST_EMAIL=qumailtest71@gmail.com
    set QUMAIL_TEST_PASSWORD=<app password>
    python -m pytest tests/integration/test_live_email.py -q -m live

or simply  scripts/live_regression.bat  (asks for the account, runs the matrix, saves the log).
The provider (Gmail / Yahoo) is detected from the address, so the same file covers both.
"""
from __future__ import annotations

import os
import time
import uuid

import pytest

from qumail.crypto import pipeline
from qumail.email.auth_help import provider_for_address
from qumail.email.imap_client import IMAPClient
from qumail.email.smtp_client import SMTPClient
from qumail.km.client import KMClient

pytestmark = pytest.mark.live

EMAIL = os.environ.get("QUMAIL_TEST_EMAIL", "")
PASSWORD = os.environ.get("QUMAIL_TEST_PASSWORD", "")
KM_URL = os.environ.get("QUMAIL_KM_URL", "http://127.0.0.1:5000")
PROVIDER = provider_for_address(EMAIL) or os.environ.get("QUMAIL_TEST_PROVIDER", "Gmail")

needs_creds = pytest.mark.skipif(not (EMAIL and PASSWORD), reason="set QUMAIL_TEST_EMAIL / QUMAIL_TEST_PASSWORD")


@pytest.fixture(scope="module")
def live_km():
    km = KMClient(KM_URL)
    try:
        km.status()
    except Exception as exc:                                       # noqa: BLE001 - any failure → skip
        pytest.skip(f"KM simulator not running at {KM_URL}: {exc}")
    return km


def _round_trip(level: int, files: list[str], km, hybrid: bool = False):
    subject = f"QuMail regression L{level}{'H' if hybrid else ''} {uuid.uuid4().hex[:8]}"
    body = f"regression body level {level} {uuid.uuid4().hex}"
    prepared, wire = pipeline.prepare(level, body, files, km, hybrid)

    smtp = SMTPClient(PROVIDER, EMAIL, PASSWORD)
    smtp.send(EMAIL, subject, prepared.body, prepared.headers(), wire)

    imap = IMAPClient(PROVIDER, EMAIL, PASSWORD)
    imap.connect()
    found = None
    try:
        for _ in range(18):                                        # poll up to ~90 s
            for item in imap.fetch_inbox(limit=15):
                if item.subject == subject:
                    found = imap.fetch_message(item.uid)
                    break
            if found:
                break
            time.sleep(5)
    finally:
        imap.close()
    assert found, f"{PROVIDER}: mail '{subject}' did not arrive within 90 s"
    assert found.level == level
    pipeline.open_message(found, km)
    assert found.body.startswith(body)                             # provider may append a footer
    return found


@needs_creds
@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_text_only_round_trip(level, live_km):
    _round_trip(level, [], live_km)


@needs_creds
@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_round_trip_with_attachment(level, live_km, tmp_path):
    f = tmp_path / f"attach_L{level}.txt"
    f.write_text("attachment payload " + uuid.uuid4().hex * 20)    # ~700 bytes, fits one OTP key
    found = _round_trip(level, [str(f)], live_km)
    names = [a.filename for a in found.attachments]
    assert f.name in names, names
    att = next(a for a in found.attachments if a.filename == f.name)
    assert att.data == f.read_bytes()                              # byte-identical after decrypt


@needs_creds
def test_round_trip_hybrid_level3_binary(live_km, tmp_path):
    f = tmp_path / "photo.bin"
    f.write_bytes(os.urandom(60_000))                              # too big for pure OTP, fine for hybrid
    found = _round_trip(3, [str(f)], live_km, hybrid=True)
    assert found.attachments[0].data == f.read_bytes()
