"""SCRUM-61 — performance test: large attachments + OTP key exhaustion.

Runs against the in-memory FakeKM (tests/conftest.py) so numbers reflect the
crypto pipeline only, not network or Gmail.  Marked ``perf``: excluded from the
quick unit run, executed by ``pytest -m perf`` and by ``tools/perf_report.py``.

Budgets below are deliberately generous (CI runners are slow); the real
measurements are written to docs/testing/PERFORMANCE.md by the report tool.
"""
from __future__ import annotations

import os
import time

import pytest

from qumail.crypto import envelope, limits, pipeline
from qumail.km.client import NoKeysAvailable

from ..conftest import FakeKM

pytestmark = pytest.mark.perf

MB = 1024 * 1024


def _tmp_file(tmp_path, size: int, name: str = "blob.bin") -> str:
    p = tmp_path / name
    p.write_bytes(os.urandom(size))
    return str(p)


def _roundtrip(level: int, text: str, files, km, hybrid=False):
    """prepare → (simulated transport) → open_message ; returns elapsed seconds (enc, dec)."""
    t0 = time.perf_counter()
    prepared, blobs = pipeline.prepare(level, text, files, km, hybrid)
    t1 = time.perf_counter()
    msg = _FakeMail(prepared, blobs, level)
    pipeline.open_message(msg, km)
    t2 = time.perf_counter()
    assert msg.body == text
    return t1 - t0, t2 - t1


class _Att:
    def __init__(self, filename, data):
        self.filename, self.data, self.content_type = filename, data, "application/octet-stream"


class _FakeMail:
    """Minimal stand-in for imap_client.EmailMessage as seen by pipeline.open_message."""

    def __init__(self, prepared, blobs, level):
        self.level = level
        self.key_id = prepared.key_id
        self.body = prepared.body
        self.attachments = [_Att(n, d) for n, d in blobs if isinstance(d, (bytes, bytearray))]


# --------------------------------------------------------------------------- #
# 1. Large attachments — AES-based levels must stay fast up to the 15 MB limit
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("level", [2, 4])
@pytest.mark.parametrize("size_mb", [1, 5, 15])
def test_large_attachment_aes_levels(tmp_path, level, size_mb):
    km = FakeKM()
    f = _tmp_file(tmp_path, size_mb * MB)
    enc, dec = _roundtrip(level, "perf", [f], km)
    assert enc < 10 and dec < 10, f"Level {level} {size_mb} MB: enc {enc:.2f}s dec {dec:.2f}s"
    # exactly one 1 KB key per mail regardless of attachment size
    assert km.status()["reserved"] == 1


def test_level3_hybrid_large_attachment_costs_two_keys(tmp_path):
    km = FakeKM()
    f = _tmp_file(tmp_path, 15 * MB)
    enc, dec = _roundtrip(3, "hybrid perf", [f], km, hybrid=True)
    assert enc < 10 and dec < 10
    assert km.status()["reserved"] == 2            # OTP body key + AES attachment key


def test_level3_full_otp_needs_key_equal_to_payload(tmp_path):
    """Pure OTP on a 60 KB file consumes ~60 keys — correct but shows why hybrid exists."""
    km = FakeKM(keys=100)
    f = _tmp_file(tmp_path, 60 * 1024)
    _roundtrip(3, "x", [f], km)
    assert km.status()["reserved"] >= 60


def test_attachment_limit_is_enforced_before_touching_km(tmp_path):
    km = FakeKM()
    f = _tmp_file(tmp_path, limits.MAX_FILE_BYTES + 1)
    problem = pipeline.check_capacity(2, "too big", [f], km)
    assert problem and "max" in problem.lower()
    assert km.status()["reserved"] == 0            # no key wasted


# --------------------------------------------------------------------------- #
# 2. OTP key exhaustion — bank of 100 × 1 KB keys
# --------------------------------------------------------------------------- #
def test_otp_exhaustion_is_predicted_and_blocked():
    km = FakeKM(keys=100)
    text = "A" * 900                                  # < 1 KB → one key per mail
    sent = 0
    while pipeline.check_capacity(3, text, [], km) is None:
        pipeline.prepare(3, text, [], km)
        sent += 1
    assert sent == 100                                 # every key used exactly once
    msg = pipeline.check_capacity(3, text, [], km)
    assert msg and "Not enough quantum key" in msg     # user is told *before* sending
    with pytest.raises(NoKeysAvailable):
        km.request_key(1)                              # and the KM itself refuses


def test_exhaustion_with_attachment_suggests_hybrid(tmp_path):
    km = FakeKM(keys=5)                                # tiny bank
    f = _tmp_file(tmp_path, 20 * 1024)
    msg = pipeline.check_capacity(3, "hi", [f], km)
    assert msg and "Hybrid" in msg                     # 20 KB OTP impossible with 5 KB of key
    assert pipeline.check_capacity(3, "hi", [f], km, hybrid=True) is None   # hybrid fits (2 keys)


def test_level2_survives_long_after_otp_bank_is_gone():
    """Level 2/4 cost 1 key per mail; after OTP exhaustion only Level 1 is possible — by design."""
    km = FakeKM(keys=100)
    for _ in range(100):
        pipeline.prepare(2, "m", [], km)
    assert km.status()["available"] == 0
    assert pipeline.check_capacity(2, "m", [], km) is not None
    assert pipeline.check_capacity(1, "m", [], km) is None


def test_failed_send_burns_key_so_it_is_never_reused():
    km = FakeKM(keys=3)
    prepared, _ = pipeline.prepare(3, "burn me", [], km)
    pipeline.burn_key(prepared, km)
    assert km.state[prepared.key_id.split("+")[0]] == "CONSUMED"
    assert km.status()["available"] == 2


def test_envelope_overhead_is_small():
    """Base64 + JSON envelope must not blow up the mail size (provider limit is 25 MB)."""
    km = FakeKM()
    text = "x" * 10_000
    prepared, _ = pipeline.prepare(2, text, [], km)
    assert len(prepared.body) < len(text) * 1.6
    assert envelope.parse_envelope(prepared.body)["level"] == 2
