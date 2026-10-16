"""QuMail message envelope + Level 1 (plain) codec.

SCRUM-28 (Day 7): Level 1 wired end-to-end. Level 2 in level2.py (SCRUM-Day8). Levels 3/4 plug into the same
`encrypt()` / `decrypt()` entry points (crypto modules by Umang).

Envelope (mail body for level >= 2) is a JSON object:
    {"qumail": 1, "level": 2, "key_id": "...", "nonce": "<b64>", "ciphertext": "<b64>", "tag": "<b64>"}
Level 1 sends the plain text body unchanged and only sets the X-QuMail-Level: 1 header.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Dict, Optional

HDR_LEVEL = "X-QuMail-Level"
HDR_KEYID = "X-QuMail-KeyID"

LEVELS: Dict[int, str] = {
    1: "Level 1 — Plain text (no encryption)",
    2: "Level 2 — Quantum-aided AES-256-GCM",
    3: "Level 3 — One-Time Pad",
    4: "Level 4 — Extra (PQC / hybrid)",
}


@dataclass
class Prepared:
    """What goes on the wire."""
    body: str
    level: int
    key_id: Optional[str] = None

    def headers(self) -> Dict[str, str]:
        h = {HDR_LEVEL: str(self.level)}
        if self.key_id:
            h[HDR_KEYID] = self.key_id
        return h


class QuMailCryptoError(Exception):
    pass


# -- Level 1 ----------------------------------------------------------------
def level1_encrypt(plaintext: str, **_) -> Prepared:
    """Level 1: identity — text is sent as-is, tagged with the level header."""
    return Prepared(body=plaintext, level=1)


def level1_decrypt(body: str, **_) -> str:
    return body


# -- registry: other levels register here when their modules land -----------
_ENCRYPTORS: Dict[int, Callable[..., Prepared]] = {1: level1_encrypt}
_DECRYPTORS: Dict[int, Callable[..., str]] = {1: level1_decrypt}


def register_level(level: int, encryptor: Callable[..., Prepared], decryptor: Callable[..., str]) -> None:
    _ENCRYPTORS[level] = encryptor
    _DECRYPTORS[level] = decryptor


def available_levels() -> Dict[int, str]:
    return {k: v for k, v in LEVELS.items() if k in _ENCRYPTORS}


def encrypt(level: int, plaintext: str, **kw) -> Prepared:
    if level not in _ENCRYPTORS:
        raise QuMailCryptoError(f"Level {level} not available yet")
    return _ENCRYPTORS[level](plaintext, **kw)


def decrypt(level: int, body: str, **kw) -> str:
    if level not in _DECRYPTORS:
        raise QuMailCryptoError(f"Level {level} not available yet")
    return _DECRYPTORS[level](body, **kw)


def parse_envelope(body: str) -> Optional[dict]:
    """Return the JSON envelope dict if `body` contains a QuMail envelope, else None.

    Tolerates text appended after the JSON (e.g. antivirus footers, signatures).
    """
    if not body:
        return None
    start = body.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(body[start:])
    except ValueError:
        return None
    return obj if isinstance(obj, dict) and obj.get("qumail") == 1 else None


def load_levels() -> None:
    """Import level modules so they register themselves (call once at app start)."""
    import importlib
    for mod in ("qumail.crypto.level2", "qumail.crypto.level3", "qumail.crypto.level4"):
        try:
            importlib.import_module(mod)
        except ImportError:
            pass  # module not written yet
