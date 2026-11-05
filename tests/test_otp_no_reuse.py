"""SCRUM-64 — security review: a quantum key is used exactly once for encryption.

Properties checked (unit level, FakeKM):
  P1  every send gets a key id that was never issued before
  P2  a key that was issued is never issued again, even if the send failed (burned)
  P3  inside one Level-3 message no key byte is used twice (body / attachments / MAC are disjoint slices)
  P4  hybrid Level 3 uses two different keys for body and attachments
  P5  Level 2/4 never reuse a nonce for the same key (fresh nonce per encryption)
  P6  decrypting with a different key of the same length fails (MAC/GCM), so a wrong or
      re-assigned key can never silently produce output
  P7  after the whole bank is used, no further encrypted send is possible
"""
from __future__ import annotations

import base64
import json
import os
import secrets

import pytest

from qumail.crypto import envelope, level3, pipeline
from qumail.crypto.envelope import QuMailCryptoError
from qumail.km.client import KeyConsumed, NoKeysAvailable

from .conftest import FakeKM


def _ids(key_id: str):
    return set(key_id.split("+"))


# P1 / P2 ------------------------------------------------------------------------
@pytest.mark.parametrize("level", [2, 3, 4])
def test_every_send_uses_fresh_key_ids(level):
    km = FakeKM(keys=30)
    seen = set()
    for i in range(10):
        prepared, _ = pipeline.prepare(level, f"msg {i}", [], km)
        ids = _ids(prepared.key_id)
        assert not (ids & seen), f"key re-issued: {ids & seen}"
        seen |= ids
    assert km.status()["available"] == 30 - len(seen)


def test_burned_key_is_never_issued_again():
    km = FakeKM(keys=3)
    p1, _ = pipeline.prepare(3, "fail", [], km)
    pipeline.burn_key(p1, km)                           # send failed → CONSUMED
    issued = set()
    for _ in range(2):
        p, _ = pipeline.prepare(3, "ok", [], km)
        issued |= _ids(p.key_id)
    assert not (issued & _ids(p1.key_id))
    with pytest.raises(NoKeysAvailable):
        km.request_key(1)
    with pytest.raises(KeyConsumed):
        km.get_key(p1.key_id)                            # and it can't even be read back


# P3 -----------------------------------------------------------------------------
def test_level3_key_slices_are_disjoint_and_cover_once(tmp_path):
    body = "hello otp " * 10                             # 100 bytes
    atts = [("a.bin", os.urandom(300)), ("b.bin", os.urandom(50))]
    key = os.urandom(level3.key_bytes_needed(len(body.encode()), [300, 50]) + 500)
    prepared, blobs = level3.encrypt(body, key_material=key, key_id="QK0001", attachments=atts)

    env = json.loads(prepared.body)
    used = []                                           # (start, end) ranges of key actually used
    ct = base64.b64decode(env["ciphertext"])
    used.append((0, len(ct)))
    for (_, blob) in blobs:
        off = int.from_bytes(blob[:4], "big")
        used.append((off, off + len(blob) - 4))
    total = env["total_len"]
    used.append((total, total + level3.MAC_BYTES))      # MAC key slice

    used.sort()
    for (s1, e1), (s2, e2) in zip(used, used[1:], strict=False):
        assert e1 <= s2, f"overlapping key ranges {(s1, e1)} and {(s2, e2)}"
    assert used[0][0] == 0 and used[-1][1] == total + level3.MAC_BYTES   # contiguous, nothing double-used


def test_level3_rejects_key_shorter_than_payload():
    key = os.urandom(40)
    with pytest.raises(QuMailCryptoError, match="OTP needs"):
        level3.encrypt("x" * 20, key_material=key, key_id="QK1", attachments=[("f", b"y" * 20)])


# P4 -----------------------------------------------------------------------------
def test_hybrid_uses_two_distinct_keys(tmp_path):
    km = FakeKM()
    f = tmp_path / "f.bin"
    f.write_bytes(os.urandom(2048))
    prepared, _ = pipeline.prepare(3, "body", [str(f)], km, hybrid=True)
    body_ids, att_ids = _ids(prepared.key_id), set(prepared.extra_key_ids)
    assert att_ids and not (body_ids & att_ids)


# P5 -----------------------------------------------------------------------------
@pytest.mark.parametrize("level", [2, 4])
def test_aes_levels_use_fresh_nonce_per_message(level):
    key = os.urandom(1024)
    nonces = set()
    for _ in range(20):
        p = envelope.encrypt(level, "same text", key_material=key, key_id="QK0001")
        env = json.loads(p.body)
        # level 2 keeps the nonce as a field; level 4 stores it as the first 12 bytes of the blob
        n = env.get("nonce") or base64.b64decode(env["ciphertext"])[:12]
        assert n not in nonces
        nonces.add(n)


# P6 -----------------------------------------------------------------------------
@pytest.mark.parametrize("level", [2, 3, 4])
def test_wrong_key_of_same_length_never_decrypts(level):
    k1, k2 = os.urandom(1024), os.urandom(1024)
    if level == 3:
        p, _ = level3.encrypt("secret", key_material=k1, key_id="QK1")
        with pytest.raises(QuMailCryptoError, match="Integrity"):
            level3.decrypt(p.body, key_material=k2)
    else:
        p = envelope.encrypt(level, "secret", key_material=k1, key_id="QK1")
        with pytest.raises(QuMailCryptoError):
            envelope.decrypt(level, p.body, key_material=k2)


def test_level3_tampered_ciphertext_is_detected():
    key = os.urandom(1024)
    p, _ = level3.encrypt("attack at dawn", key_material=key, key_id="QK1")
    env = json.loads(p.body)
    ct = bytearray(base64.b64decode(env["ciphertext"]))
    ct[0] ^= 0x01                                        # flip one bit → OTP alone would decrypt to a different word
    env["ciphertext"] = base64.b64encode(bytes(ct)).decode()
    with pytest.raises(QuMailCryptoError, match="Integrity"):
        level3.decrypt(json.dumps(env), key_material=key)


# P7 -----------------------------------------------------------------------------
def test_exhausted_bank_blocks_all_encrypted_levels():
    km = FakeKM(keys=2)
    pipeline.prepare(2, "a", [], km)
    pipeline.prepare(4, "b", [], km)
    for level in (2, 3, 4):
        assert pipeline.check_capacity(level, "c", [], km) is not None
        with pytest.raises(NoKeysAvailable):
            pipeline.prepare(level, "c", [], km)


# receiver side ----------------------------------------------------------------
def test_consume_after_decrypt_option(monkeypatch):
    """With QUMAIL_CONSUME_AFTER_DECRYPT=1 the receiver burns the key once the mail is read."""
    from qumail import config
    km = FakeKM()
    prepared, _ = pipeline.prepare(2, "read once", [], km)

    class M:
        level, key_id, body, attachments = 2, prepared.key_id, prepared.body, []

    monkeypatch.setenv("QUMAIL_CONSUME_AFTER_DECRYPT", "1")
    config.reload(dotenv=False)
    try:
        pipeline.open_message(M(), km)
        assert km.state[prepared.key_id] == "CONSUMED"
        with pytest.raises(KeyConsumed):
            pipeline.open_message(M(), km)               # second read impossible — true one-time
    finally:
        monkeypatch.delenv("QUMAIL_CONSUME_AFTER_DECRYPT")
        config.reload(dotenv=False)


def test_default_keeps_key_readable_for_reopen():
    km = FakeKM()
    prepared, _ = pipeline.prepare(2, "re-open", [], km)

    class M:
        level, key_id, body, attachments = 2, prepared.key_id, prepared.body, []

    pipeline.open_message(M(), km)
    pipeline.open_message(M(), km)                       # can be re-opened
    assert km.state[prepared.key_id] == "RESERVED"        # but is still never re-issued for encryption
    for _ in range(5):
        assert prepared.key_id not in _ids(pipeline.prepare(2, "x", [], km)[0].key_id)


def test_random_source_is_cryptographic():
    """Nonces come from `secrets`, never `random` (bandit B311 also enforces this in CI)."""
    import inspect

    from qumail.crypto import level2, level4
    for mod in (level2, level4):
        src = inspect.getsource(mod)
        assert "secrets.token_bytes" in src and "import random" not in src
    assert secrets.token_bytes(12) != secrets.token_bytes(12)
