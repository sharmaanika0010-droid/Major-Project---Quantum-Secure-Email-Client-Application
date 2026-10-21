from types import SimpleNamespace

import pytest

from qumail.crypto import pipeline
from qumail.crypto.envelope import QuMailCryptoError
from qumail.km.client import KeyConsumed, NoKeysAvailable


class Att:
    def __init__(self, filename, data, content_type="application/octet-stream"):
        self.filename, self.data, self.content_type = filename, data, content_type


def _msg(prepared, wire_atts):
    return SimpleNamespace(level=prepared.level, key_id=prepared.key_id, body=prepared.body,
                           attachments=[Att(n, d) for n, d in wire_atts])


@pytest.mark.parametrize("level", [1, 2, 3])
def test_send_then_open_roundtrip(tmp_path, km, level):
    f = tmp_path / "note.txt"
    f.write_bytes(b"attachment payload")
    prepared, wire = pipeline.prepare(level, "hello pipeline", [str(f)], km)
    if level == 1:
        assert wire == [str(f)]
        wire = [("note.txt", f.read_bytes())]
    else:
        assert wire[0][0] == "note.txt.qenc"
    msg = _msg(prepared, wire)
    note = pipeline.open_message(msg, km)
    assert msg.body == "hello pipeline"
    assert msg.attachments[0].filename == "note.txt"
    assert msg.attachments[0].data == b"attachment payload"
    assert (note is None) if level == 1 else ("Decrypted" in note)


def test_level3_reserves_enough_keys(km, tmp_path):
    f = tmp_path / "big.bin"
    f.write_bytes(b"x" * 3000)
    prepared, _ = pipeline.prepare(3, "", [str(f)], km)
    assert prepared.key_id.count("+") == 2          # 3000 + 32 bytes -> 3 keys
    assert km.status()["reserved"] == 3


def test_check_capacity_blocks_oversized_level3(km, tmp_path):
    f = tmp_path / "huge.bin"
    f.write_bytes(b"x" * (200 * 1024))
    msg = pipeline.check_capacity(3, "", [str(f)], km)
    assert msg and "Not enough quantum key" in msg
    assert km.status()["reserved"] == 0             # nothing reserved


def test_check_capacity_level2_small_need(km, tmp_path):
    f = tmp_path / "huge.bin"
    f.write_bytes(b"x" * (200 * 1024))
    assert pipeline.check_capacity(2, "", [str(f)], km) is None


def test_check_capacity_empty_bank(empty_km):
    assert "Not enough quantum key" in pipeline.check_capacity(2, "hi", [], empty_km)


def test_check_capacity_offline(offline_km):
    assert "Cannot reach" in pipeline.check_capacity(2, "hi", [], offline_km)


def test_prepare_raises_when_bank_empty(empty_km):
    with pytest.raises(NoKeysAvailable):
        pipeline.prepare(2, "hi", [], empty_km)


def test_burn_key_marks_consumed(km):
    prepared, _ = pipeline.prepare(2, "hi", [], km)
    pipeline.burn_key(prepared, km)
    assert km.state[prepared.key_id] == "CONSUMED"
    with pytest.raises(KeyConsumed):
        km.get_key(prepared.key_id)


def test_open_message_without_key_id():
    msg = SimpleNamespace(level=2, key_id=None, body="{}", attachments=[])
    with pytest.raises(QuMailCryptoError):
        pipeline.open_message(msg, None)
