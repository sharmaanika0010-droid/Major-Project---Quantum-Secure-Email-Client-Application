"""Level 3 — One-Time Pad with quantum key (SCRUM Day 9).

Rules
- Key material must be at least as long as (body + all attachments) + 32 bytes.
  The extra 32 bytes are used once as an HMAC-SHA256 key for integrity (OTP alone
  has no integrity protection).
- Every byte of key is used exactly once: body takes key[0:len(body)], each
  attachment takes the next slice; the offset is stored in the attachment blob.
- The KM hands out whole 1 KB keys, so the request is rounded up by the KM.

Body envelope: {"qumail":1,"level":3,"key_id":..,"ciphertext":b64,"mac":b64,"total_len":N}
Attachment blob (<name>.qenc):  offset(4 bytes BE) | ciphertext
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import json
from typing import List, Tuple

from qumail.crypto.envelope import Prepared, QuMailCryptoError, parse_envelope, register_level

MAC_BYTES = 32


def key_bytes_needed(body_len: int, attachment_sizes: List[int]) -> int:
    return body_len + sum(attachment_sizes) + MAC_BYTES


def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, key))


def _mac(key_material: bytes, total_len: int, *chunks: bytes) -> bytes:
    mac_key = key_material[total_len:total_len + MAC_BYTES]
    h = hmac.new(mac_key, digestmod=hashlib.sha256)
    for c in chunks:
        h.update(c)
    return h.digest()


def encrypt(plaintext: str, *, key_material: bytes, key_id: str, attachments: List[Tuple[str, bytes]] = (), **_):
    """Returns (Prepared, [(name.qenc, blob), ...])."""
    pt = plaintext.encode("utf-8")
    sizes = [len(d) for _, d in attachments]
    total = len(pt) + sum(sizes)
    if len(key_material) < total + MAC_BYTES:
        raise QuMailCryptoError(
            f"OTP needs {total + MAC_BYTES} bytes of key, KM returned {len(key_material)}")

    ct = _xor(pt, key_material[:len(pt)])
    offset = len(pt)
    blobs = []
    for name, data in attachments:
        blobs.append((name + ".qenc", offset.to_bytes(4, "big") + _xor(data, key_material[offset:offset + len(data)])))
        offset += len(data)
    mac = _mac(key_material, total, ct, *(b for _, b in blobs))
    env = {"qumail": 1, "level": 3, "key_id": key_id, "total_len": total,
           "ciphertext": base64.b64encode(ct).decode(), "mac": base64.b64encode(mac).decode()}
    return Prepared(body=json.dumps(env, indent=1), level=3, key_id=key_id), blobs


def decrypt(body: str, *, key_material: bytes, attachments: List[Tuple[str, bytes]] = (), **_):
    """Returns (plaintext, [(name, data), ...]) after verifying the MAC."""
    env = parse_envelope(body)
    if not env or env.get("level") != 3:
        raise QuMailCryptoError("Not a Level 3 QuMail envelope")
    try:
        ct = base64.b64decode(env["ciphertext"])
        mac = base64.b64decode(env["mac"])
        total = int(env["total_len"])
    except (KeyError, ValueError) as exc:
        raise QuMailCryptoError("Corrupted Level 3 envelope") from exc
    if len(key_material) < total + MAC_BYTES:
        raise QuMailCryptoError("Key material shorter than message — wrong key?")
    blobs = [b for _, b in attachments]
    if not hmac.compare_digest(mac, _mac(key_material, total, ct, *blobs)):
        raise QuMailCryptoError("Integrity check failed — wrong key or tampered message")
    pt = _xor(ct, key_material[:len(ct)])
    out = []
    for name, blob in attachments:
        off = int.from_bytes(blob[:4], "big")
        data = blob[4:]
        out.append((name[:-5] if name.endswith(".qenc") else name, _xor(data, key_material[off:off + len(data)])))
    return pt.decode("utf-8", errors="replace"), out


register_level(3, encrypt, decrypt)
