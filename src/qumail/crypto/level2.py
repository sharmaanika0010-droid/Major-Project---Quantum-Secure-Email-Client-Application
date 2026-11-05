"""Level 2 — Quantum-aided AES-256-GCM.

Quantum key material from the KM is never used directly: a 256-bit AES key is
derived with HKDF-SHA256 (context "QuMail-L2"). Each message/attachment gets a
fresh 96-bit nonce; GCM tag gives integrity.

Body envelope (JSON, see envelope.py):
  {"qumail":1,"level":2,"key_id":"QK0001","nonce":b64,"ciphertext":b64,"tag":b64}
Attachment blob (file renamed <name>.qenc):  nonce(12) | tag(16) | ciphertext
"""
from __future__ import annotations

import base64
import json
import secrets

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF

from qumail.crypto.envelope import Prepared, QuMailCryptoError, parse_envelope, register_level

KEY_BYTES_NEEDED = 32          # how much quantum material we ask the KM for
_CONTEXT = b"QuMail-L2-AES256GCM"


def derive_key(key_material: bytes) -> bytes:
    if len(key_material) < 16:
        raise QuMailCryptoError("Key material too short")
    return HKDF(key_material, 32, salt=b"", hashmod=SHA256, context=_CONTEXT)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def _unb64(s: str) -> bytes:
    return base64.b64decode(s)


# -- bytes (attachments) --------------------------------------------------
def encrypt_bytes(data: bytes, aes_key: bytes) -> bytes:
    nonce = secrets.token_bytes(12)
    ct, tag = AES.new(aes_key, AES.MODE_GCM, nonce=nonce).encrypt_and_digest(data)
    return nonce + tag + ct


def decrypt_bytes(blob: bytes, aes_key: bytes) -> bytes:
    if len(blob) < 28:
        raise QuMailCryptoError("Encrypted attachment is corrupted")
    nonce, tag, ct = blob[:12], blob[12:28], blob[28:]
    try:
        return AES.new(aes_key, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(ct, tag)
    except ValueError as exc:
        raise QuMailCryptoError("Integrity check failed — wrong key or tampered data") from exc


# -- text (mail body) -----------------------------------------------------
def encrypt(plaintext: str, *, key_material: bytes, key_id: str, **_) -> Prepared:
    aes_key = derive_key(key_material)
    nonce = secrets.token_bytes(12)
    ct, tag = AES.new(aes_key, AES.MODE_GCM, nonce=nonce).encrypt_and_digest(plaintext.encode("utf-8"))
    env = {"qumail": 1, "level": 2, "key_id": key_id, "nonce": _b64(nonce), "ciphertext": _b64(ct), "tag": _b64(tag)}
    body = json.dumps(env, indent=1)
    return Prepared(body=body, level=2, key_id=key_id)


def decrypt(body: str, *, key_material: bytes, **_) -> str:
    env = parse_envelope(body)
    if not env or env.get("level") != 2:
        raise QuMailCryptoError("Not a Level 2 QuMail envelope")
    aes_key = derive_key(key_material)
    try:
        pt = AES.new(aes_key, AES.MODE_GCM, nonce=_unb64(env["nonce"])).decrypt_and_verify(_unb64(env["ciphertext"]), _unb64(env["tag"]))
    except (ValueError, KeyError) as exc:
        raise QuMailCryptoError("Integrity check failed — wrong key or tampered message") from exc
    return pt.decode("utf-8", errors="replace")


register_level(2, encrypt, decrypt)
