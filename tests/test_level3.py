import os

import pytest

from qumail.crypto import envelope, level3
from qumail.crypto.envelope import QuMailCryptoError

KEY = os.urandom(2048)


def test_roundtrip_with_attachments():
    atts = [("a.txt", b"alpha"), ("b.bin", os.urandom(300))]
    p, blobs = envelope.encrypt(3, "otp body", key_material=KEY, key_id="QK0001+QK0002", attachments=atts)
    assert p.level == 3 and p.headers()["X-QuMail-KeyID"] == "QK0001+QK0002"
    assert [n for n, _ in blobs] == ["a.txt.qenc", "b.bin.qenc"]
    text, plain = envelope.decrypt(3, p.body, key_material=KEY, attachments=blobs)
    assert text == "otp body"
    assert plain == atts


def test_key_bytes_needed_includes_mac():
    assert level3.key_bytes_needed(10, [5, 5]) == 20 + level3.MAC_BYTES


def test_key_too_short_rejected():
    with pytest.raises(QuMailCryptoError):
        envelope.encrypt(3, "x" * 100, key_material=os.urandom(50), key_id="k")


def test_wrong_key_detected():
    p, blobs = envelope.encrypt(3, "otp", key_material=KEY, key_id="k")
    with pytest.raises(QuMailCryptoError):
        envelope.decrypt(3, p.body, key_material=os.urandom(2048), attachments=blobs)


def test_tampered_attachment_detected():
    p, blobs = envelope.encrypt(3, "otp", key_material=KEY, key_id="k", attachments=[("f", b"data")])
    name, blob = blobs[0]
    bad = blob[:-1] + bytes([blob[-1] ^ 1])
    with pytest.raises(QuMailCryptoError):
        envelope.decrypt(3, p.body, key_material=KEY, attachments=[(name, bad)])


def test_key_bytes_are_not_reused_between_body_and_attachment():
    """Body uses key[0:n]; attachment must start at offset n (no overlap)."""
    p, blobs = envelope.encrypt(3, "abcd", key_material=KEY, key_id="k", attachments=[("f", b"wxyz")])
    offset = int.from_bytes(blobs[0][1][:4], "big")
    assert offset == 4
