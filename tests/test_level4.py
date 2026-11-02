import base64
import json
import os
from types import SimpleNamespace

import pytest

from qumail.crypto import envelope, level4, pipeline
from qumail.crypto.envelope import QuMailCryptoError

KEY = os.urandom(1024)


class Att:
    def __init__(self, filename, data):
        self.filename, self.data, self.content_type = filename, data, "application/octet-stream"


def test_registered_and_labelled():
    assert 4 in envelope.available_levels()
    assert "Double layer" in envelope.available_levels()[4]


def test_two_independent_keys():
    a, c = level4.derive_keys(KEY)
    assert len(a) == 32 and len(c) == 32 and a != c
    assert level4.derive_keys(KEY) == (a, c)


def test_body_roundtrip_and_envelope_fields():
    p = envelope.encrypt(4, "double ✓", key_material=KEY, key_id="QK0007")
    env = json.loads(p.body)
    assert env["level"] == 4 and env["cipher"].startswith("AES-256-GCM")
    assert p.headers() == {"X-QuMail-Level": "4", "X-QuMail-KeyID": "QK0007"}
    assert envelope.decrypt(4, p.body, key_material=KEY) == "double ✓"


def test_outer_layer_hides_inner_layer():
    """Ciphertext must not expose the inner AES-GCM blob (it is itself encrypted)."""
    data = b"plaintext"
    keys = level4.derive_keys(KEY)
    blob = level4.encrypt_bytes(data, keys)
    assert len(blob) == len(data) + 2 * 28
    # decrypting the outer layer alone yields the inner blob, not the plaintext
    from Crypto.Cipher import ChaCha20_Poly1305
    inner = ChaCha20_Poly1305.new(key=keys[1], nonce=blob[:12]).decrypt_and_verify(blob[28:], blob[12:28])
    assert data not in inner


def test_wrong_key_and_tamper_detected():
    p = envelope.encrypt(4, "secret", key_material=KEY, key_id="k")
    with pytest.raises(QuMailCryptoError):
        envelope.decrypt(4, p.body, key_material=os.urandom(1024))
    env = json.loads(p.body)
    blob = bytearray(base64.b64decode(env["ciphertext"]))
    blob[-1] ^= 1
    env["ciphertext"] = base64.b64encode(bytes(blob)).decode()
    with pytest.raises(QuMailCryptoError):
        envelope.decrypt(4, json.dumps(env), key_material=KEY)


def test_inner_layer_tamper_detected():
    """Re-encrypt a tampered inner blob with the right outer key: inner GCM must still fail."""
    from Crypto.Cipher import ChaCha20_Poly1305
    keys = level4.derive_keys(KEY)
    blob = level4.encrypt_bytes(b"abc", keys)
    inner = bytearray(ChaCha20_Poly1305.new(key=keys[1], nonce=blob[:12]).decrypt_and_verify(blob[28:], blob[12:28]))
    inner[-1] ^= 1
    n2 = os.urandom(12)
    ct, tag = ChaCha20_Poly1305.new(key=keys[1], nonce=n2).encrypt_and_digest(bytes(inner))
    with pytest.raises(QuMailCryptoError):
        level4.decrypt_bytes(n2 + tag + ct, keys)


def test_fresh_nonces():
    keys = level4.derive_keys(KEY)
    assert level4.encrypt_bytes(b"x", keys) != level4.encrypt_bytes(b"x", keys)


def test_pipeline_roundtrip_with_attachment(tmp_path, km):
    f = tmp_path / "doc.pdf"
    f.write_bytes(os.urandom(5000))
    assert pipeline.check_capacity(4, "hi", [str(f)], km) is None
    prepared, wire = pipeline.prepare(4, "level four", [str(f)], km)
    assert km.status()["reserved"] == 1 and wire[0][0] == "doc.pdf.qenc"
    msg = SimpleNamespace(level=4, key_id=prepared.key_id, body=prepared.body, attachments=[Att(n, d) for n, d in wire])
    note = pipeline.open_message(msg, km)
    assert msg.body == "level four" and msg.attachments[0].data == f.read_bytes()
    assert "double layer" in note.lower()
