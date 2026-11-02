import os

import pytest

from qumail.crypto import envelope, level2
from qumail.crypto.envelope import QuMailCryptoError

KEY = os.urandom(1024)


def test_body_roundtrip():
    p = envelope.encrypt(2, "secret text ✓", key_material=KEY, key_id="QK0001")
    assert p.level == 2 and p.headers()["X-QuMail-KeyID"] == "QK0001"
    assert "secret" not in p.body
    assert envelope.decrypt(2, p.body, key_material=KEY) == "secret text ✓"


def test_wrong_key_fails_integrity():
    p = envelope.encrypt(2, "secret", key_material=KEY, key_id="QK0001")
    with pytest.raises(QuMailCryptoError):
        envelope.decrypt(2, p.body, key_material=os.urandom(1024))


def test_tampered_ciphertext_detected():
    import base64
    import json
    p = envelope.encrypt(2, "secret", key_material=KEY, key_id="QK0001")
    env = json.loads(p.body)
    ct = bytearray(base64.b64decode(env["ciphertext"]))
    ct[0] ^= 0xFF
    env["ciphertext"] = base64.b64encode(bytes(ct)).decode()
    with pytest.raises(QuMailCryptoError):
        envelope.decrypt(2, json.dumps(env), key_material=KEY)


def test_nonce_is_fresh_per_message():
    a = envelope.encrypt(2, "same", key_material=KEY, key_id="k").body
    b = envelope.encrypt(2, "same", key_material=KEY, key_id="k").body
    assert a != b


def test_attachment_bytes_roundtrip():
    aes = level2.derive_key(KEY)
    blob = level2.encrypt_bytes(b"\x00\x01file bytes", aes)
    assert blob[28:] != b"\x00\x01file bytes"
    assert level2.decrypt_bytes(blob, aes) == b"\x00\x01file bytes"


def test_derive_key_is_deterministic_and_256_bit():
    assert level2.derive_key(KEY) == level2.derive_key(KEY)
    assert len(level2.derive_key(KEY)) == 32
