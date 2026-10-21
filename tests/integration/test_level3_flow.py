"""SCRUM-45 — Integration: full Level 3 (OTP) flow with attachment against the real KM simulator.

Sender side : check_capacity -> prepare (keys reserved in KM) -> build the MIME mail
Transport   : the exact bytes a mail server would carry (email.message_from_bytes)
Receiver side: parse headers -> pipeline.open_message (fetches key by ID from KM) -> plaintext + file
"""
from __future__ import annotations

import email
import email.policy
import hashlib
import os
from email.message import EmailMessage
from types import SimpleNamespace

import pytest

from qumail.crypto import pipeline
from qumail.crypto.envelope import QuMailCryptoError
from qumail.km.client import KeyConsumed, NoKeysAvailable

pytestmark = pytest.mark.integration


class _Att:
    def __init__(self, part):
        self.filename = part.get_filename()
        self.content_type = part.get_content_type()
        self.data = part.get_payload(decode=True)


def _build_mail(prepared, wire_atts) -> bytes:
    """Same structure SMTPClient produces: headers + text body + attachments."""
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = "a@test", "b@test", "L3 integration"
    for k, v in prepared.headers().items():
        msg[k] = v
    msg.set_content(prepared.body)
    for name, data in wire_atts:
        msg.add_attachment(data, maintype="application", subtype="octet-stream", filename=name)
    return msg.as_bytes()


def _receive(raw: bytes):
    m = email.message_from_bytes(raw, policy=email.policy.default)
    body = next(p for p in m.walk() if p.get_content_type() == "text/plain").get_content()
    atts = [_Att(p) for p in m.walk() if p.get_filename()]
    return SimpleNamespace(level=int(m.get("X-QuMail-Level", 1)), key_id=m.get("X-QuMail-KeyID"),
                           body=body.rstrip("\n"), attachments=atts)


def test_level3_full_flow_with_attachment(tmp_path, km):
    # --- arrange: a 3 KB binary attachment + message
    payload = os.urandom(3 * 1024)
    f = tmp_path / "secret.bin"
    f.write_bytes(payload)
    text = "Level 3 integration — body ✓"
    before = km.status()

    # --- sender
    assert pipeline.check_capacity(3, text, [str(f)], km) is None
    prepared, wire = pipeline.prepare(3, text, [str(f)], km)
    assert prepared.level == 3 and "+" in prepared.key_id          # OTP needed >1 key
    assert wire[0][0] == "secret.bin.qenc"
    assert payload not in wire[0][1]                               # ciphertext ≠ plaintext
    assert km.status()["reserved"] == before["reserved"] + len(prepared.key_id.split("+"))

    # --- transport
    raw = _build_mail(prepared, wire)
    assert payload not in raw and text.encode() not in raw        # nothing leaks on the wire
    assert b"X-QuMail-Level: 3" in raw and b"X-QuMail-KeyID: " in raw

    # --- receiver (fresh objects; only the KM key id links the two sides)
    msg = _receive(raw)
    note = pipeline.open_message(msg, km)
    assert msg.body == text
    assert msg.attachments[0].filename == "secret.bin"
    assert hashlib.sha256(msg.attachments[0].data).hexdigest() == hashlib.sha256(payload).hexdigest()
    assert "Level 3" in note and prepared.key_id.split("+")[0] in note


def test_level3_key_count_matches_size(tmp_path, km):
    f = tmp_path / "f.bin"
    f.write_bytes(b"x" * 2048)                                     # 2048 + 32 MAC -> 3 keys
    prepared, _ = pipeline.prepare(3, "", [str(f)], km)
    assert len(prepared.key_id.split("+")) == 3


def test_level2_full_flow_with_attachment(tmp_path, km):
    f = tmp_path / "pic.png"
    f.write_bytes(os.urandom(50 * 1024))                           # 50 KB on a single 1 KB key
    prepared, wire = pipeline.prepare(2, "aes body", [str(f)], km)
    assert "+" not in prepared.key_id
    msg = _receive(_build_mail(prepared, wire))
    pipeline.open_message(msg, km)
    assert msg.body == "aes body" and msg.attachments[0].data == f.read_bytes()


def test_wrong_recipient_key_rejected(tmp_path, km):
    """Tampering with the key id in transit must fail integrity, never return garbage."""
    prepared, wire = pipeline.prepare(3, "hi", [], km)
    other, _ = pipeline.prepare(3, "x" * 10, [], km)
    msg = _receive(_build_mail(prepared, wire))
    msg.key_id = other.key_id
    with pytest.raises(QuMailCryptoError):
        pipeline.open_message(msg, km)


def test_burned_key_cannot_be_fetched(km):
    prepared, _ = pipeline.prepare(3, "will fail to send", [], km)
    pipeline.burn_key(prepared, km)
    with pytest.raises(KeyConsumed):
        km.get_key(prepared.key_id)


def test_capacity_check_against_real_bank(tmp_path, km):
    avail = km.available_bytes()
    f = tmp_path / "big.bin"
    f.write_bytes(b"x" * (avail + 1))
    msg = pipeline.check_capacity(3, "", [str(f)], km)
    assert msg and "Not enough quantum key" in msg
    assert km.available_bytes() == avail                           # nothing was reserved


def test_depletion_raises_typed_error(km):
    """Drain the remaining bank, then one more request must be NoKeysAvailable (409)."""
    remaining = km.available_bytes()
    if remaining:
        km.request_key(remaining)
    assert km.available_bytes() == 0
    with pytest.raises(NoKeysAvailable):
        km.request_key(1)
    assert "Not enough quantum key" in pipeline.check_capacity(2, "hi", [], km)
