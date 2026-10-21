"""Shared fixtures — a fake Key Manager so tests never need the Flask simulator."""
from __future__ import annotations

import os

import pytest

from qumail.crypto import envelope
from qumail.km.client import IssuedKey, KeyConsumed, KMUnreachable, NoKeysAvailable

envelope.load_levels()


class FakeKM:
    """In-memory stand-in for KMClient with the same public methods."""

    def __init__(self, keys: int = 100, key_size: int = 1024, online: bool = True):
        self.key_size = key_size
        self.online = online
        self.bank = {f"QK{i:04d}": os.urandom(key_size) for i in range(1, keys + 1)}
        self.state = {k: "AVAILABLE" for k in self.bank}

    def _up(self):
        if not self.online:
            raise KMUnreachable("Cannot reach Key Manager at http://fake")

    def status(self):
        self._up()
        return {
            "total": len(self.bank),
            "key_size_bytes": self.key_size,
            "available": sum(s == "AVAILABLE" for s in self.state.values()),
            "reserved": sum(s == "RESERVED" for s in self.state.values()),
            "consumed": sum(s == "CONSUMED" for s in self.state.values()),
        }

    def request_key(self, key_bytes: int) -> IssuedKey:
        self._up()
        need = -(-key_bytes // self.key_size)
        free = [k for k, s in self.state.items() if s == "AVAILABLE"]
        if len(free) < need:
            raise NoKeysAvailable(f"No quantum keys available — need {need}, {len(free)} available")
        chosen = free[:need]
        for k in chosen:
            self.state[k] = "RESERVED"
        return IssuedKey("+".join(chosen), b"".join(self.bank[k] for k in chosen))

    def get_key(self, key_id: str) -> IssuedKey:
        self._up()
        for k in key_id.split("+"):
            if self.state[k] == "CONSUMED":
                raise KeyConsumed(f"Key {k} was already consumed")
        return IssuedKey(key_id, b"".join(self.bank[k] for k in key_id.split("+")))

    def consume(self, key_id: str) -> None:
        self._up()
        for k in key_id.split("+"):
            self.state[k] = "CONSUMED"


@pytest.fixture
def km():
    return FakeKM()


@pytest.fixture
def empty_km():
    return FakeKM(keys=0)


@pytest.fixture
def offline_km():
    return FakeKM(online=False)
