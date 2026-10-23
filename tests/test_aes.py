"""SCRUM-23 | Unit tests for Level 2 AES module (src/crypto/aes.py).

Ticket: SCRUM-23
Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from crypto import aes  # noqa: E402

KEY = bytes(range(256)) * 4  # 1 KB stand-in for a QKD key block
KID = "QK0001"


def test_roundtrip_text():
    env = aes.encrypt("Hello Bob".encode(), KEY, KID)
    assert aes.decrypt(env, KEY) == b"Hello Bob"


def test_roundtrip_binary_and_empty():
    blob = os.urandom(5000)
    assert aes.decrypt(aes.encrypt(blob, KEY, KID, "application/pdf"), KEY) == blob
    assert aes.decrypt(aes.encrypt(b"", KEY, KID), KEY) == b""


def test_plaintext_not_in_envelope():
    assert "Hello Bob" not in aes.encrypt(b"Hello Bob", KEY, KID)


def test_envelope_headers_and_parse():
    env = aes.parse_envelope(aes.encrypt(b"x", KEY, KID, "application/pdf"))
    assert env.key_id == KID and env.content_type == "application/pdf"
    assert len(env.nonce) == 12 and len(env.ciphertext) == 1 + 16


def test_unique_nonce_per_message():
    a = aes.parse_envelope(aes.encrypt(b"same", KEY, KID))
    b = aes.parse_envelope(aes.encrypt(b"same", KEY, KID))
    assert a.nonce != b.nonce and a.ciphertext != b.ciphertext


def test_wrong_key_rejected():
    env = aes.encrypt(b"secret", KEY, KID)
    with pytest.raises(aes.QuMailCryptoError):
        aes.decrypt(env, os.urandom(1024))


def test_tampered_ciphertext_rejected():
    parsed = aes.parse_envelope(aes.encrypt(b"secret message", KEY, KID))
    ct = bytearray(parsed.ciphertext)
    ct[0] ^= 1
    parsed.ciphertext = bytes(ct)
    with pytest.raises(aes.QuMailCryptoError):
        aes.decrypt_envelope(parsed, KEY)


def test_swapped_key_id_rejected():
    env = aes.encrypt(b"secret", KEY, KID)
    with pytest.raises(aes.QuMailCryptoError):
        aes.decrypt(env.replace("Key-ID: QK0001", "Key-ID: QK0002"), KEY)


@pytest.mark.parametrize("bad", [
    "hello",
    "QUMAIL-V1\nSecurity-Level: 3\nAlgorithm: OTP\nKey-ID: QK1\nNonce: AAAA\n\nAAAA",
    "QUMAIL-V1\nSecurity-Level: 2\nAlgorithm: AES-256-GCM\n\nAAAA",
    "QUMAIL-V1\nSecurity-Level: 2\nAlgorithm: AES-256-GCM\nKey-ID: QK1\nNonce: !!!\n\n!!!",
])
def test_malformed_envelope_rejected(bad):
    with pytest.raises(aes.QuMailCryptoError):
        aes.decrypt(bad, KEY)


def test_short_key_material_rejected():
    with pytest.raises(aes.QuMailCryptoError):
        aes.encrypt(b"x", b"short", KID)


def test_crlf_tolerant():
    env = aes.encrypt(b"line", KEY, KID).replace("\n", "\r\n")
    assert aes.decrypt(env, KEY) == b"line"


def test_is_envelope():
    assert aes.is_envelope(aes.encrypt(b"x", KEY, KID))
    assert not aes.is_envelope("just a normal email") and not aes.is_envelope("")
