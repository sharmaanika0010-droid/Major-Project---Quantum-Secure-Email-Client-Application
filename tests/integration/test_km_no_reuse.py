"""SCRUM-64 — the REAL Key Manager simulator never hands out a key twice."""
from __future__ import annotations

import pytest

from qumail.km.client import KeyConsumed, NoKeysAvailable

pytestmark = pytest.mark.integration


def test_simulator_never_reissues_a_key(km):
    issued = []
    st = km.status()
    for _ in range(min(10, st["available"])):
        issued.append(km.request_key(1).key_id)
    assert len(issued) == len(set(issued))                 # all distinct
    km.consume(issued[0])
    with pytest.raises(KeyConsumed):
        km.get_key(issued[0])                               # 410 after consume
    # the consumed id must not come back from a new request either
    more = [km.request_key(1).key_id for _ in range(min(5, km.status()["available"]))]
    assert issued[0] not in more and not (set(more) & set(issued))


def test_simulator_refuses_more_than_available(km):
    """Asking for more key material than the pool holds is refused (409) — nothing is reserved."""
    st = km.status()
    before = st["available"]
    with pytest.raises(NoKeysAvailable):
        km.request_key((before + 1) * st["key_size_bytes"])
    assert km.status()["available"] == before
