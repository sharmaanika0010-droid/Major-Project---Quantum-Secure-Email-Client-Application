"""Level 4 — Extra security: double-layer authenticated encryption (SCRUM Day 15, "extra option").

Why: Level 2 relies on a single primitive (AES-GCM). Level 4 wraps the message in two
independent AEAD ciphers with two independently derived keys, so a break of either
algorithm (or a flawed implementation of one) does not expose the plaintext.

    inner = AES-256-GCM        (key_A = HKDF(quantum key, "QuMail-L4-AES"))
    outer = ChaCha20-Poly1305  (key_C = HKDF(quantum key, "QuMail-L4-CHACHA"))
    blob  = nonce_C(12) | tag_C(16) | ChaCha20( nonce_A(12) | tag_A(16) | AES-GCM(plaintext) )

The two keys come from the same 1 KB quantum key via HKDF with different context
strings, so the KM cost is identical to Level 2 (one key per mail). Nonces are fresh
per message / attachment. This is "cascade encryption" (cf. TrueCrypt/VeraCrypt
AES-Twofish cascades) — not post-quantum key exchange, which is out of scope because
no key exchange happens: keys are already shared through the KM.

Body envelope: {"qumail":1,"level":4,"key_id":..,"ciphertext":b64(blob)}
Attachment blob (<name>.qenc): same blob layout.
"""
from __future__ import annotations

import base64
import json
import secrets

from Crypto.Cipher import AES, ChaCha20_Poly1305
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF

from qumail.crypto.envelope import Prepared, QuMailCryptoError, parse_envelope, register_level

KEY_BYTES_NEEDED = 64            # asked from KM (rounded up to one 1 KB key)
_CTX_AES = b"QuMail-L4-AES256GCM"
_CTX_CHACHA = b"QuMail-L4-CHACHA20POLY1305"
_HDR = 28                        # nonce(12) + tag(16)


def derive_keys(key_material: bytes) -> tuple[bytes, bytes]:
    """Two independent 256-bit keys from one quantum key."""
    if len(key_material) < 32:
        raise QuMailCryptoError("Key material too short for Level 4")
    k_aes = HKDF(key_material, 32, salt=b"", hashmod=SHA256, context=_CTX_AES)
    k_cha = HKDF(key_material, 32, salt=b"", hashmod=SHA256, context=_CTX_CHACHA)
    return k_aes, k_cha


def encrypt_bytes(data: bytes, keys: tuple[bytes, bytes]) -> bytes:
    k_aes, k_cha = keys
    n1 = secrets.token_bytes(12)
    ct1, t1 = AES.new(k_aes, AES.MODE_GCM, nonce=n1).encrypt_and_digest(data)
    inner = n1 + t1 + ct1
    n2 = secrets.token_bytes(12)
    ct2, t2 = ChaCha20_Poly1305.new(key=k_cha, nonce=n2).encrypt_and_digest(inner)
    return n2 + t2 + ct2


def decrypt_bytes(blob: bytes, keys: tuple[bytes, bytes]) -> bytes:
    k_aes, k_cha = keys
    if len(blob) < 2 * _HDR:
        raise QuMailCryptoError("Encrypted data is corrupted")
    try:
        inner = ChaCha20_Poly1305.new(key=k_cha, nonce=blob[:12]).decrypt_and_verify(blob[_HDR:], blob[12:_HDR])
        return AES.new(k_aes, AES.MODE_GCM, nonce=inner[:12]).decrypt_and_verify(inner[_HDR:], inner[12:_HDR])
    except ValueError as exc:
        raise QuMailCryptoError("Integrity check failed — wrong key or tampered data") from exc


def encrypt(plaintext: str, *, key_material: bytes, key_id: str, **_) -> Prepared:
    blob = encrypt_bytes(plaintext.encode("utf-8"), derive_keys(key_material))
    env = {"qumail": 1, "level": 4, "key_id": key_id, "cipher": "AES-256-GCM+ChaCha20-Poly1305",
           "ciphertext": base64.b64encode(blob).decode()}
    return Prepared(body=json.dumps(env, indent=1), level=4, key_id=key_id)


def decrypt(body: str, *, key_material: bytes, **_) -> str:
    env = parse_envelope(body)
    if not env or env.get("level") != 4:
        raise QuMailCryptoError("Not a Level 4 QuMail envelope")
    try:
        blob = base64.b64decode(env["ciphertext"])
    except (KeyError, ValueError) as exc:
        raise QuMailCryptoError("Corrupted Level 4 envelope") from exc
    return decrypt_bytes(blob, derive_keys(key_material)).decode("utf-8", errors="replace")


register_level(4, encrypt, decrypt)
