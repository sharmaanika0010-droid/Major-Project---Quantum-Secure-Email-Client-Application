"""SCRUM-67 — bug bash BB-07: a mail opened against a different Key Manager must say so clearly."""
from __future__ import annotations

import json
import os

import pytest

from qumail.crypto import envelope, pipeline
from qumail.crypto.envelope import KeyMismatch, QuMailCryptoError, key_fingerprint

from .conftest import FakeKM


class _Msg:
    def __init__(self, prepared, attachments=None):
        self.level, self.key_id, self.body = prepared.level, prepared.key_id, prepared.body
        self.attachments = attachments or []


def _two_banks():
    """Sender KM and a receiver KM with the same key ids but different random material."""
    return FakeKM(), FakeKM()


@pytest.mark.parametrize("level", [2, 3, 4])
def test_envelope_carries_key_fingerprint(level):
    km = FakeKM()
    prepared, _ = pipeline.prepare(level, "hello", [], km)
    env = json.loads(prepared.body)
    assert env["key_fp"] == key_fingerprint(km.get_key(prepared.key_id).material)
    assert len(env["key_fp"]) == 12                    # short public hash, not key material


@pytest.mark.parametrize("level", [2, 3, 4])
def test_wrong_key_manager_gives_clear_message(level):
    sender_km, receiver_km = _two_banks()
    prepared, _ = pipeline.prepare(level, "hello", [], sender_km)
    with pytest.raises(KeyMismatch, match="not using the same Key Manager"):
        pipeline.open_message(_Msg(prepared), receiver_km)


def test_same_key_manager_still_decrypts():
    km = FakeKM()
    prepared, _ = pipeline.prepare(3, "same bank", [], km)
    m = _Msg(prepared)
    assert pipeline.open_message(m, km)
    assert m.body == "same bank"


def test_hybrid_checks_attachment_key_too(tmp_path):
    sender_km, receiver_km = _two_banks()
    f = tmp_path / "a.bin"
    f.write_bytes(os.urandom(100))
    prepared, _ = pipeline.prepare(3, "body", [str(f)], sender_km, hybrid=True)
    with pytest.raises(KeyMismatch):
        pipeline.open_message(_Msg(prepared), receiver_km)


def test_old_mail_without_fingerprint_gets_hint():
    """Mails sent before SCRUM-67 have no key_fp: a MAC failure now carries the wrong-KM hint."""
    sender_km, receiver_km = _two_banks()
    key = sender_km.request_key(64)
    prepared = envelope.encrypt(2, "legacy", key_material=key.material, key_id=key.key_id)
    assert "key_fp" not in json.loads(prepared.body)
    with pytest.raises(QuMailCryptoError, match="Most likely cause"):
        pipeline.open_message(_Msg(prepared), receiver_km)


def test_fingerprint_is_not_reversible_and_distinct():
    a, b = os.urandom(1024), os.urandom(1024)
    assert key_fingerprint(a) != key_fingerprint(b)
    assert key_fingerprint(a) == key_fingerprint(a)
    assert key_fingerprint(a) not in a.hex()
