import os
from types import SimpleNamespace

import pytest

from qumail.crypto import limits, pipeline
from qumail.km.client import KeyConsumed


class Att:
    def __init__(self, filename, data):
        self.filename, self.data, self.content_type = filename, data, "application/octet-stream"


def _mk(tmp_path, name, n):
    f = tmp_path / name
    f.write_bytes(os.urandom(n) if n else b"")
    return str(f)


# --- size validation ---------------------------------------------------------
def test_validate_ok(tmp_path):
    assert limits.validate([_mk(tmp_path, "a.bin", 100), _mk(tmp_path, "b.bin", 2000)]) is None


def test_validate_rejects_empty_duplicate_missing(tmp_path):
    e = _mk(tmp_path, "e.bin", 0)
    assert "empty" in limits.validate([e])
    a = _mk(tmp_path, "a.bin", 10)
    assert "twice" in limits.validate([a, a])
    assert "Cannot read" in limits.validate([str(tmp_path / "nope.bin")])


def test_validate_too_many(tmp_path):
    files = [_mk(tmp_path, f"f{i}.bin", 10) for i in range(limits.MAX_FILES + 1)]
    assert "Too many" in limits.validate(files)


def test_validate_per_file_and_total(tmp_path, monkeypatch):
    monkeypatch.setattr(limits, "MAX_FILE_BYTES", 1000)
    monkeypatch.setattr(limits, "MAX_TOTAL_BYTES", 1500)
    assert "max" in limits.validate([_mk(tmp_path, "big.bin", 1001)])
    assert "total" in limits.validate([_mk(tmp_path, "a.bin", 900), _mk(tmp_path, "b.bin", 900)])


def test_human_and_summary(tmp_path):
    assert limits.human(512) == "512 B" and limits.human(1536) == "1.5 KB" and limits.human(3 * 1024 * 1024) == "3.0 MB"
    s = limits.summary([_mk(tmp_path, "x.txt", 2048)])
    assert s.startswith("1 file, 2.0 KB") and "x.txt" in s
    assert limits.summary([]) == "No attachments"


def test_check_capacity_runs_size_validation_first(tmp_path, km):
    assert "empty" in pipeline.check_capacity(1, "", [_mk(tmp_path, "e.bin", 0)], km)


# --- multiple attachments ----------------------------------------------------
@pytest.mark.parametrize("level", [2, 3])
def test_multiple_attachments_roundtrip(tmp_path, km, level):
    files = [_mk(tmp_path, f"f{i}.bin", 300 + i) for i in range(4)]
    prepared, wire = pipeline.prepare(level, "multi", files, km)
    msg = SimpleNamespace(level=level, key_id=prepared.key_id, body=prepared.body, attachments=[Att(n, d) for n, d in wire])
    pipeline.open_message(msg, km)
    assert [a.filename for a in msg.attachments] == [f"f{i}.bin" for i in range(4)]
    for a, f in zip(msg.attachments, files, strict=True):
        assert a.data == open(f, "rb").read()


# --- hybrid: OTP body + AES attachments --------------------------------------
def test_hybrid_uses_little_key_for_big_file(tmp_path, km):
    big = _mk(tmp_path, "big.bin", 40 * 1024)                  # 40 KB would need 41 OTP keys
    from qumail.crypto import level2, level3
    assert pipeline.key_bytes_for(3, "hi", [big], hybrid=True) == 2 + level3.MAC_BYTES + level2.KEY_BYTES_NEEDED
    prepared, wire = pipeline.prepare(3, "hi", [big], km, hybrid=True)
    assert km.status()["reserved"] == 2                        # 1 OTP key + 1 AES key
    assert prepared.extra_key_ids and wire[0][0] == "big.bin.qenc"
    msg = SimpleNamespace(level=3, key_id=prepared.key_id, body=prepared.body, attachments=[Att(n, d) for n, d in wire])
    note = pipeline.open_message(msg, km)
    assert msg.body == "hi" and msg.attachments[0].data == open(big, "rb").read()
    assert "Level 2 attachments" in note


def test_hybrid_without_attachments_is_plain_level3(km):
    prepared, wire = pipeline.prepare(3, "text only", [], km, hybrid=True)
    assert wire == [] and not getattr(prepared, "extra_key_ids", None)


def test_burn_key_burns_both_hybrid_keys(tmp_path, km):
    prepared, _ = pipeline.prepare(3, "x", [_mk(tmp_path, "a.bin", 10)], km, hybrid=True)
    pipeline.burn_key(prepared, km)
    for kid in [prepared.key_id] + prepared.extra_key_ids:
        with pytest.raises(KeyConsumed):
            km.get_key(kid)


def test_capacity_tip_suggests_hybrid(tmp_path, km):
    big = _mk(tmp_path, "huge.bin", 200 * 1024)
    assert "Hybrid" in pipeline.check_capacity(3, "", [big], km)
    assert pipeline.check_capacity(3, "", [big], km, hybrid=True) is None
