"""SCRUM-23 | Tests for Level 2 send/receive flow using in-memory fakes (no Gmail, no KM server).

Ticket: SCRUM-23
Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from crypto import aes, level2  # noqa: E402
from email_service.gmail_adapter import Attachment, EmailMessage  # noqa: E402


class FakeKM:
    def __init__(self, n=3, down=False):
        self.keys = {f"QK{i:04d}": [os.urandom(1024), "AVAILABLE"] for i in range(1, n + 1)}
        self.down = down

    def request_key(self, nbytes=32):
        if self.down:
            raise level2.KMError("Key Manager unreachable")
        for kid, v in self.keys.items():
            if v[1] == "AVAILABLE":
                v[1] = "RESERVED"
                return kid, v[0]
        raise level2.KMError("KM error 409: Insufficient key material")

    def fetch_key(self, kid):
        if kid not in self.keys or self.keys[kid][1] == "CONSUMED":
            raise level2.KMError("KM error 410: Key already consumed")
        return self.keys[kid][0]

    def consume(self, kid):
        self.keys[kid][1] = "CONSUMED"


class FakeProvider:
    """Stores what 'Gmail' would receive."""
    def __init__(self):
        self.sent = []

    def send_message(self, to, subject, body, attachments=None):
        atts = []
        for p in attachments or []:
            with open(p, "rb") as f:
                atts.append(Attachment(os.path.basename(p), "application/octet-stream", f.read()))
        self.sent.append(EmailMessage("m1", to=to, subject=subject, body=body, attachments=atts))
        return "m1"


def test_send_then_receive_with_attachment(tmp_path):
    km, prov = FakeKM(), FakeProvider()
    f = tmp_path / "note.txt"
    f.write_bytes(b"attachment bytes \x00\x01\x02")
    msg_id, key_id = level2.send_level2(prov, km, "bob@x.com", "Hi", "Hello Bob", [str(f)])
    assert msg_id == "m1" and key_id == "QK0001"

    wire = prov.sent[0]
    assert "Hello Bob" not in wire.body and level2.is_qumail_message(wire)
    assert wire.attachments[0].filename == "note.txt.qumail"
    assert b"attachment bytes" not in wire.attachments[0].data

    out = level2.read_level2(prov, km, wire)
    assert out.body == "Hello Bob"
    assert out.attachments == [("note.txt", b"attachment bytes \x00\x01\x02")]
    assert km.keys[key_id][1] == "CONSUMED"


def test_key_consumed_after_read_cannot_be_read_again():
    km, prov = FakeKM(), FakeProvider()
    level2.send_level2(prov, km, "b@x.com", "s", "once")
    level2.read_level2(prov, km, prov.sent[0])
    with pytest.raises(level2.KMError):
        level2.read_level2(prov, km, prov.sent[0])


def test_km_down_sends_nothing():
    prov = FakeProvider()
    with pytest.raises(level2.KMError):
        level2.send_level2(prov, FakeKM(down=True), "b@x.com", "s", "secret")
    assert prov.sent == []


def test_key_bank_exhausted_sends_nothing():
    km, prov = FakeKM(n=1), FakeProvider()
    level2.send_level2(prov, km, "b@x.com", "s", "one")
    with pytest.raises(level2.KMError):
        level2.send_level2(prov, km, "b@x.com", "s", "two")
    assert len(prov.sent) == 1


def test_tampered_body_not_consumed():
    km, prov = FakeKM(), FakeProvider()
    level2.send_level2(prov, km, "b@x.com", "s", "hello")
    wire = prov.sent[0]
    wire.body = wire.body.replace("Key-ID: QK0001", "Key-ID: QK0002")
    with pytest.raises(aes.QuMailCryptoError):
        level2.read_level2(prov, km, wire)
    assert km.keys["QK0001"][1] == "RESERVED"  # failed decrypt must not burn the key
