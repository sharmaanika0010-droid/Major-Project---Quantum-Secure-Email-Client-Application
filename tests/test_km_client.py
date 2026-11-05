"""KMClient against a fake `requests` — covers status/request/get/consume + error mapping."""
import base64
import json

import pytest

from qumail.km import client as kmc


class FakeResp:
    def __init__(self, status, payload, url=""):
        self.status_code, self._p, self.url, self.text = status, payload, url, json.dumps(payload)
        self.ok = status < 400

    def json(self):
        return self._p


@pytest.fixture
def fake_requests(monkeypatch):
    calls = {}

    def get(url, timeout):
        calls["get"] = url
        if url.endswith("/keys/status"):
            return FakeResp(200, {"total": 100, "available": 5, "key_size_bytes": 1024})
        if url.endswith("/keys/QK0410"):
            return FakeResp(410, {"detail": "Key already consumed"}, url)
        if url.endswith("/keys/QK0404"):
            return FakeResp(404, {"detail": "Unknown key id"}, url)
        return FakeResp(200, {"key_id": url.rsplit("/", 1)[1], "key_material": base64.b64encode(b"m" * 1024).decode()}, url)

    def post(url, json, timeout):
        calls["post"] = (url, json)
        if url.endswith("/keys/request"):
            if json["key_bytes"] > 5 * 1024:
                return FakeResp(409, {"detail": "Insufficient key material"}, url)
            n = -(-json["key_bytes"] // 1024)
            return FakeResp(200, {"key_ids": [f"QK{i:04d}" for i in range(1, n + 1)],
                                  "key_material": base64.b64encode(b"k" * 1024 * n).decode()}, url)
        return FakeResp(200, {"consumed": json["key_ids"]}, url)

    monkeypatch.setattr(kmc.requests, "get", get)
    monkeypatch.setattr(kmc.requests, "post", post)
    return calls


def test_status_and_available_bytes(fake_requests):
    c = kmc.KMClient("http://km:5000/")
    assert c.status()["available"] == 5
    assert c.available_bytes() == 5 * 1024
    assert fake_requests["get"] == "http://km:5000/keys/status"


def test_request_key_joins_multiple_keys(fake_requests):
    k = kmc.KMClient("http://km").request_key(2500)
    assert k.key_id == "QK0001+QK0002+QK0003" and len(k.material) == 3072
    assert k.ids == ["QK0001", "QK0002", "QK0003"]


def test_request_key_depleted_raises_typed_error(fake_requests):
    with pytest.raises(kmc.NoKeysAvailable):
        kmc.KMClient("http://km").request_key(10_000)


def test_get_key_consumed_and_unknown(fake_requests):
    c = kmc.KMClient("http://km")
    with pytest.raises(kmc.KeyConsumed):
        c.get_key("QK0410")
    with pytest.raises(kmc.KMError):
        c.get_key("QK0404")
    assert len(c.get_key("QK0001+QK0002").material) == 2048


def test_consume_posts_split_ids(fake_requests):
    kmc.KMClient("http://km").consume("QK0001+QK0002")
    assert fake_requests["post"] == ("http://km/keys/consume", {"key_ids": ["QK0001", "QK0002"]})


def test_unreachable(monkeypatch):
    def boom(*a, **k):
        raise kmc.requests.ConnectionError("refused")
    monkeypatch.setattr(kmc.requests, "get", boom)
    with pytest.raises(kmc.KMUnreachable):
        kmc.KMClient("http://127.0.0.1:1").status()
