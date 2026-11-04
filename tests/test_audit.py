"""SCRUM-58: key-usage audit trail."""
from __future__ import annotations

import json

import pytest

from qumail import audit as audit_mod
from qumail.audit import AuditError, AuditLog
from qumail.crypto import envelope, pipeline


@pytest.fixture
def log(tmp_path, monkeypatch):
    a = AuditLog(tmp_path / "audit.log")
    monkeypatch.setattr(audit_mod, "_log", a)
    return a


def test_entries_are_json_lines_with_chain(log):
    log.log("key_requested", key_id="QK0001", bytes=1024)
    log.log("mail_encrypted", level=2, key_id="QK0001")
    lines = log.path.read_text().splitlines()
    assert len(lines) == 2
    first, second = (json.loads(ln) for ln in lines)
    assert first["event"] == "key_requested" and first["prev"] == "0" * 64
    assert second["prev"] == audit_mod._h(lines[0])
    assert log.verify() == (True, -1)


def test_tampering_is_detected(log):
    for i in range(3):
        log.log("key_consumed", key_id=f"QK000{i}")
    lines = log.path.read_text().splitlines()
    lines[1] = lines[1].replace("QK0001", "QK0009")
    log.path.write_text("\n".join(lines) + "\n")
    ok, bad = log.verify()
    assert ok is False and bad == 2            # line after the edited one no longer matches


def test_secrets_are_refused(log):
    with pytest.raises(AuditError):
        log.log("key_requested", key_material="abc")
    with pytest.raises(AuditError):
        log.log("login", password="x")
    assert log.entries() == []


def test_tail_and_summary(log):
    for _ in range(5):
        log.log("key_requested", key_id="QK0001")
    log.log("mail_sent", level=2)
    assert len(log.tail(3)) == 3
    assert log.key_summary() == {"key_requested": 5, "mail_sent": 1}


def test_write_failure_does_not_raise(tmp_path, monkeypatch):
    a = AuditLog(tmp_path)                     # a directory → open() fails
    a.log("login", address="a@b.co")           # must not raise


# -- integration with the crypto pipeline ------------------------------------

def test_pipeline_logs_key_lifecycle(log, km, tmp_path):
    envelope.load_levels()
    prepared, _ = pipeline.prepare(2, "hello", [], km)
    events = [e["event"] for e in log.entries()]
    assert events == ["key_requested", "mail_encrypted"]
    enc = log.entries()[1]
    assert enc["level"] == 2 and enc["key_id"] == prepared.key_id
    pipeline.burn_key(prepared, km)
    assert log.entries()[-1]["event"] == "key_burned"
    raw = log.path.read_text()
    assert "hello" not in raw                                       # message text never logged


def test_log_never_contains_key_material(log, km):
    envelope.load_levels()
    prepared, _ = pipeline.prepare(4, "double layer", [], km)
    key = km.get_key(prepared.key_id)
    import base64
    raw = log.path.read_text()
    assert base64.b64encode(key.material).decode()[:16] not in raw
    assert key.material.hex()[:16] not in raw
