"""SCRUM-23 | Level 2 (Quantum-aided AES): QKD key block -> HKDF-SHA256 -> AES-256-GCM.

Ticket: SCRUM-23
Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com

Pure crypto + envelope helpers. No network, no email, no Key Manager calls here.

Design (SCRUM-11 research):
  * AES key = HKDF-SHA256(QKD key material, info = "QuMail-L2|<key_id>")  -> 32 bytes
  * 96-bit random nonce per message
  * GCM AAD = "QUMAIL-V1|2|AES-256-GCM|<key_id>" so the header cannot be swapped
  * Only the key_id travels in the email, never key bytes
"""
import base64
import textwrap
from dataclasses import dataclass

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.Random import get_random_bytes

MAGIC = "QUMAIL-V1"
SECURITY_LEVEL = "2"
ALGORITHM = "AES-256-GCM"
NONCE_LEN = 12
TAG_LEN = 16
AES_KEY_LEN = 32
MIN_KEY_MATERIAL = 32  # bytes of QKD material needed to seed the AES key


class QuMailCryptoError(Exception):
    """Bad key, tampered/corrupt data or malformed envelope."""


@dataclass
class Envelope:
    key_id: str
    nonce: bytes
    ciphertext: bytes  # ciphertext || 16-byte GCM tag
    content_type: str = "text/plain"
    security_level: str = SECURITY_LEVEL
    algorithm: str = ALGORITHM


def derive_key(key_material: bytes, key_id: str) -> bytes:
    """QKD key block -> 32-byte AES key. key_id is bound in via HKDF info."""
    if not isinstance(key_material, (bytes, bytearray)) or len(key_material) < MIN_KEY_MATERIAL:
        raise QuMailCryptoError(f"key material must be at least {MIN_KEY_MATERIAL} bytes")
    if not key_id:
        raise QuMailCryptoError("key_id is required")
    return HKDF(bytes(key_material), AES_KEY_LEN, b"", SHA256,
                context=b"QuMail-L2|" + key_id.encode())


def _aad(key_id: str) -> bytes:
    return f"{MAGIC}|{SECURITY_LEVEL}|{ALGORITHM}|{key_id}".encode()


def encrypt(plaintext: bytes, key_material: bytes, key_id: str,
            content_type: str = "text/plain") -> str:
    """Encrypt bytes and return the QuMail envelope as text (ready to be an email body)."""
    key = derive_key(key_material, key_id)
    nonce = get_random_bytes(NONCE_LEN)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce, mac_len=TAG_LEN)
    cipher.update(_aad(key_id))
    ct, tag = cipher.encrypt_and_digest(bytes(plaintext))
    return pack_envelope(Envelope(key_id, nonce, ct + tag, content_type))


def decrypt(envelope_text: str, key_material: bytes) -> bytes:
    """Verify + decrypt an envelope. Raises QuMailCryptoError on any failure."""
    env = parse_envelope(envelope_text)
    return decrypt_envelope(env, key_material)


def decrypt_envelope(env: Envelope, key_material: bytes) -> bytes:
    if len(env.nonce) != NONCE_LEN or len(env.ciphertext) < TAG_LEN:
        raise QuMailCryptoError("malformed envelope payload")
    key = derive_key(key_material, env.key_id)
    cipher = AES.new(key, AES.MODE_GCM, nonce=env.nonce, mac_len=TAG_LEN)
    cipher.update(_aad(env.key_id))
    try:
        return cipher.decrypt_and_verify(env.ciphertext[:-TAG_LEN], env.ciphertext[-TAG_LEN:])
    except ValueError:
        raise QuMailCryptoError("authentication failed: wrong key or data was modified") from None


# ---------------- envelope (text format, report ch.15) ----------------
def pack_envelope(env: Envelope) -> str:
    payload = base64.b64encode(env.ciphertext).decode()
    head = [
        MAGIC,
        f"Security-Level: {env.security_level}",
        f"Algorithm: {env.algorithm}",
        f"Key-ID: {env.key_id}",
        f"Nonce: {base64.b64encode(env.nonce).decode()}",
        f"Content-Type: {env.content_type}",
        "Content-Encoding: base64",
    ]
    return "\n".join(head) + "\n\n" + "\n".join(textwrap.wrap(payload, 76)) + "\n"


def is_envelope(text: str) -> bool:
    return bool(text) and text.lstrip().startswith(MAGIC)


def parse_envelope(text: str) -> Envelope:
    if not is_envelope(text):
        raise QuMailCryptoError("not a QuMail envelope")
    lines = text.strip().replace("\r\n", "\n").split("\n")
    headers, i = {}, 1
    while i < len(lines) and lines[i].strip():
        name, sep, value = lines[i].partition(":")
        if not sep:
            raise QuMailCryptoError("malformed envelope header")
        headers[name.strip().lower()] = value.strip()
        i += 1
    if headers.get("security-level") != SECURITY_LEVEL or headers.get("algorithm") != ALGORITHM:
        raise QuMailCryptoError("unsupported security level or algorithm")
    if not headers.get("key-id") or "nonce" not in headers:
        raise QuMailCryptoError("envelope is missing Key-ID or Nonce")
    try:
        nonce = base64.b64decode(headers["nonce"], validate=True)
        ct = base64.b64decode("".join(l.strip() for l in lines[i:]), validate=True)
    except ValueError:
        raise QuMailCryptoError("envelope contains invalid base64") from None
    return Envelope(headers["key-id"], nonce, ct,
                    headers.get("content-type", "text/plain"))
