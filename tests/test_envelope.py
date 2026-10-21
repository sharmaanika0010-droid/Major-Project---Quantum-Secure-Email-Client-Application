from qumail.crypto import envelope


def test_levels_registered():
    lv = envelope.available_levels()
    assert {1, 2, 3} <= set(lv)


def test_level1_roundtrip():
    p = envelope.encrypt(1, "hello")
    assert p.body == "hello" and p.level == 1
    assert p.headers() == {"X-QuMail-Level": "1"}
    assert envelope.decrypt(1, p.body) == "hello"


def test_parse_envelope_ignores_footer():
    body = '{"qumail": 1, "level": 2, "x": 1}\n--\nThis email has been checked for viruses by Avast.'
    assert envelope.parse_envelope(body)["level"] == 2


def test_parse_envelope_rejects_plain_text():
    assert envelope.parse_envelope("just a normal mail {not json}") is None
    assert envelope.parse_envelope('{"foo": 1}') is None


def test_unknown_level_raises():
    import pytest
    with pytest.raises(envelope.QuMailCryptoError):
        envelope.encrypt(9, "x")
