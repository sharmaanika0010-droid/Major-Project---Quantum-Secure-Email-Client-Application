"""Send/receive pipeline: ties KM + level modules together (Day 9).

GUI calls only two functions:
    prepare(level, text, file_paths, km)  -> (Prepared, wire_attachments)
    open_message(msg, km)                 -> note string  (mutates msg.body / msg.attachments)
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import List, Tuple

from qumail.crypto import envelope
from qumail.crypto.envelope import QuMailCryptoError
from qumail.km.client import KMClient, KMError

KEY_UNIT = 1024  # KM hands out 1 KB keys


def _read(files: List[str]) -> List[Tuple[str, bytes]]:
    return [(Path(f).name, Path(f).read_bytes()) for f in files]


def check_capacity(level: int, text: str, files: List[str], km: KMClient) -> str | None:
    """Return a human message if the KM cannot serve this message, else None."""
    if level < 2:
        return None
    if level == 3:
        from qumail.crypto import level3
        need = level3.key_bytes_needed(len(text.encode()), [Path(f).stat().st_size for f in files])
    else:
        from qumail.crypto import level2
        need = level2.KEY_BYTES_NEEDED
    try:
        st = km.status()
    except KMError as exc:
        return str(exc)
    have = st.get("available", 0) * st.get("key_size_bytes", KEY_UNIT)
    if need > have:
        return (f"Not enough quantum key: Level {level} needs {need:,} bytes "
                f"({-(-need // KEY_UNIT)} keys), KM has {have:,} bytes ({st.get('available', 0)} keys). "
                f"Shorten the message / remove attachments or use a lower level.")
    return None


def prepare(level: int, text: str, files: List[str], km: KMClient):
    """Encrypt according to level. Returns (Prepared, attachments-for-smtp)."""
    if level == 1:
        return envelope.encrypt(1, text), list(files)

    atts = _read(files)
    if level == 2:
        from qumail.crypto import level2
        key = km.request_key(level2.KEY_BYTES_NEEDED)
        prepared = envelope.encrypt(2, text, key_material=key.material, key_id=key.key_id)
        aes = level2.derive_key(key.material)
        return prepared, [(n + ".qenc", level2.encrypt_bytes(d, aes)) for n, d in atts]

    if level == 3:
        from qumail.crypto import level3
        need = level3.key_bytes_needed(len(text.encode()), [len(d) for _, d in atts])
        key = km.request_key(need)
        prepared, blobs = envelope.encrypt(3, text, key_material=key.material, key_id=key.key_id, attachments=atts)
        return prepared, blobs

    raise QuMailCryptoError(f"Level {level} not available")


def burn_key(prepared, km: KMClient) -> None:
    """Send failed after a key was reserved: mark it CONSUMED so it is never reused (Day 10)."""
    if getattr(prepared, "key_id", None):
        try:
            km.consume(prepared.key_id)
        except KMError:
            pass  # best effort — KM may be down too


def open_message(msg, km: KMClient) -> str | None:
    """Decrypt msg in place (body + attachments). Returns a status note or None for Level 1."""
    if msg.level < 2:
        return None
    if not msg.key_id:
        raise QuMailCryptoError("Encrypted message has no X-QuMail-KeyID header")
    key = km.get_key(msg.key_id)

    if msg.level == 2:
        from qumail.crypto import level2
        msg.body = envelope.decrypt(2, msg.body, key_material=key.material)
        aes = level2.derive_key(key.material)
        for att in msg.attachments:
            if att.filename.endswith(".qenc"):
                att.data = level2.decrypt_bytes(att.data, aes)
                att.filename = att.filename[:-5]
                att.content_type = mimetypes.guess_type(att.filename)[0] or "application/octet-stream"
    elif msg.level == 3:
        enc = [(a.filename, a.data) for a in msg.attachments if a.filename.endswith(".qenc")]
        msg.body, plain = envelope.decrypt(3, msg.body, key_material=key.material, attachments=enc)
        by_name = dict(plain)
        for att in msg.attachments:
            if att.filename.endswith(".qenc"):
                att.filename = att.filename[:-5]
                att.data = by_name[att.filename]
                att.content_type = mimetypes.guess_type(att.filename)[0] or "application/octet-stream"
    else:
        raise QuMailCryptoError(f"Level {msg.level} not available")
    return f"🔓 Decrypted with quantum key {msg.key_id} (Level {msg.level}, {len(key.material):,} key bytes)"
