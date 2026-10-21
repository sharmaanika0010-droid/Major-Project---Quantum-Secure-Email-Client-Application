"""Key Manager client — talks to the KM simulator (SCRUM-14, Umang).

Endpoints used (see SCRUM_Works/SCRUM-14/README.md):
  GET  /keys/status            -> counts
  POST /keys/request {key_bytes} -> key_ids[], key_material (base64)   (409 if not enough)
  GET  /keys/{key_id}          -> key_material (base64)                 (410 if consumed)
  POST /keys/consume {key_ids} -> mark consumed

Day 10 (SCRUM-39): typed errors (NoKeysAvailable / KeyConsumed / KMUnreachable),
available_bytes() for depletion warnings.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import List

import requests


class KMError(Exception):
    """Raised when the Key Manager is unreachable or returns an error."""


class KMUnreachable(KMError):
    """KM server down / wrong URL."""


class NoKeysAvailable(KMError):
    """Key bank depleted (HTTP 409 on /keys/request)."""


class KeyConsumed(KMError):
    """Key already used once (HTTP 410 on /keys/{id})."""


@dataclass
class IssuedKey:
    key_id: str          # "QK0001" or "QK0001+QK0002" when several keys were joined
    material: bytes

    @property
    def ids(self) -> List[str]:
        return self.key_id.split("+")


class KMClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _check(self, resp: requests.Response, what: str) -> dict:
        if resp.ok:
            return resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        if resp.status_code == 409 and "request" in resp.url:
            raise NoKeysAvailable(f"No quantum keys available — {detail}")
        if resp.status_code == 410:
            raise KeyConsumed(f"{what} was already consumed (one-time key cannot be reused)")
        if resp.status_code == 404:
            raise KMError(f"{what}: unknown key id")
        raise KMError(f"{what}: {detail} (HTTP {resp.status_code})")

    # -- API ------------------------------------------------------------
    def status(self) -> dict:
        try:
            return self._check(requests.get(self._url("/keys/status"), timeout=self.timeout), "KM status")
        except requests.RequestException as exc:
            raise KMUnreachable(f"Cannot reach Key Manager at {self.base_url}") from exc

    def request_key(self, key_bytes: int) -> IssuedKey:
        """Reserve `key_bytes` of quantum key material for a new message."""
        try:
            data = self._check(
                requests.post(self._url("/keys/request"), json={"key_bytes": int(key_bytes)}, timeout=self.timeout),
                "No quantum keys available",
            )
        except requests.RequestException as exc:
            raise KMUnreachable(f"Cannot reach Key Manager at {self.base_url}") from exc
        return IssuedKey("+".join(data["key_ids"]), base64.b64decode(data["key_material"]))

    def get_key(self, key_id: str) -> IssuedKey:
        """Receiver side: fetch the same key material by key_id (joined ids supported)."""
        chunks = []
        for kid in key_id.split("+"):
            try:
                data = self._check(requests.get(self._url(f"/keys/{kid}"), timeout=self.timeout), f"Key {kid}")
            except requests.RequestException as exc:
                raise KMUnreachable(f"Cannot reach Key Manager at {self.base_url}") from exc
            chunks.append(base64.b64decode(data["key_material"]))
        return IssuedKey(key_id, b"".join(chunks))

    def available_bytes(self) -> int:
        st = self.status()
        return int(st.get("available", 0)) * int(st.get("key_size_bytes", 1024))

    def consume(self, key_id: str) -> None:
        try:
            self._check(requests.post(self._url("/keys/consume"), json={"key_ids": key_id.split("+")}, timeout=self.timeout), "Consume")
        except requests.RequestException as exc:
            raise KMUnreachable(f"Cannot reach Key Manager at {self.base_url}") from exc
