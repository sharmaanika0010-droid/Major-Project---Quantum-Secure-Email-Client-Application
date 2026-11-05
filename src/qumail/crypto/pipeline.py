"""Send/receive pipeline: ties KM + level modules together (Day 9).

GUI calls only two functions:
    prepare(level, text, file_paths, km)  -> (Prepared, wire_attachments)
    open_message(msg, km)                 -> note string  (mutates msg.body / msg.attachments)
"""
from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from typing import List, Tuple

from qumail import audit
from qumail.config import get_settings
from qumail.crypto import envelope, limits
from qumail.crypto.envelope import KeyMismatch, QuMailCryptoError, key_fingerprint
from qumail.km.client import KMClient, KMError

KEY_UNIT = 1024  # KM hands out 1 KB keys


def _read(files: List[str]) -> List[Tuple[str, bytes]]:
    return [(Path(f).name, Path(f).read_bytes()) for f in files]


def key_bytes_for(level: int, text: str, files: List[str], hybrid: bool = False) -> int:
    """Key bytes a message needs. hybrid = Level 3 body + Level 2 attachments (Day 15 option)."""
    if level < 2:
        return 0
    from qumail.crypto import level2
    if level == 2:
        return level2.KEY_BYTES_NEEDED
    if level == 4:
        from qumail.crypto import level4
        return level4.KEY_BYTES_NEEDED
    from qumail.crypto import level3
    if hybrid:
        return level3.key_bytes_needed(len(text.encode()), []) + (level2.KEY_BYTES_NEEDED if files else 0)
    return level3.key_bytes_needed(len(text.encode()), [Path(f).stat().st_size for f in files])


def check_capacity(level: int, text: str, files: List[str], km: KMClient, hybrid: bool = False) -> str | None:
    """Return a human message if the mail cannot be sent (size limits or KM), else None."""
    problem = limits.validate(files)
    if problem:
        return problem
    if level < 2:
        return None
    need = key_bytes_for(level, text, files, hybrid)
    try:
        st = km.status()
    except KMError as exc:
        return str(exc)
    have = st.get("available", 0) * st.get("key_size_bytes", KEY_UNIT)
    if need > have:
        tip = ("Tip: enable 'Hybrid' (OTP body + AES attachments) or use Level 2."
               if level == 3 and files and not hybrid else "Shorten the message / remove attachments or use a lower level.")
        return (f"Not enough quantum key: Level {level} needs {need:,} bytes "
                f"({-(-need // KEY_UNIT)} keys), KM has {have:,} bytes ({st.get('available', 0)} keys). {tip}")
    return None


def _request(km: KMClient, nbytes: int, purpose: str):
    key = km.request_key(nbytes)
    audit.log("key_requested", key_id=key.key_id, bytes=nbytes, purpose=purpose)
    return key


def _stamp(prepared, material: bytes, field: str = "key_fp"):
    """Add the key fingerprint to the envelope JSON (BB-07: detect wrong Key Manager on receive)."""
    env = json.loads(prepared.body)
    env[field] = key_fingerprint(material)
    prepared.body = json.dumps(env, indent=1)
    return prepared


WRONG_KM_HINT = ("Sender and receiver are not using the same Key Manager (different key bank). "
                 "Run one KM for both sides — e.g. the same QuMail-KM.exe / keybank.csv — and send the mail again.")


def _verify_key(msg_env: dict, key_id: str, material: bytes, field: str = "key_fp") -> None:
    fp = msg_env.get(field)
    if fp and fp != key_fingerprint(material):
        audit.log("key_mismatch", key_id=key_id, expected_fp=fp, got_fp=key_fingerprint(material))
        raise KeyMismatch(f"Key {key_id} from this Key Manager is not the key the sender used. {WRONG_KM_HINT}")


def _encrypted(prepared, level: int, n_files: int, hybrid: bool = False):
    audit.log("mail_encrypted", level=level, key_id=getattr(prepared, "key_id", None),
              extra_keys=list(getattr(prepared, "extra_key_ids", [])), attachments=n_files, hybrid=hybrid)
    return prepared


def prepare(level: int, text: str, files: List[str], km: KMClient, hybrid: bool = False):
    """Encrypt according to level. Returns (Prepared, attachments-for-smtp).

    hybrid (Level 3 only): body is OTP-encrypted, attachments are AES-256-GCM with a second
    quantum key — keeps perfect secrecy for the text while big files cost one 1 KB key.
    """
    if level == 1:
        return envelope.encrypt(1, text), list(files)

    atts = _read(files)
    if level == 2:
        from qumail.crypto import level2
        key = _request(km, level2.KEY_BYTES_NEEDED, "level2")
        prepared = _stamp(envelope.encrypt(2, text, key_material=key.material, key_id=key.key_id), key.material)
        aes = level2.derive_key(key.material)
        return _encrypted(prepared, 2, len(atts)), [(n + ".qenc", level2.encrypt_bytes(d, aes)) for n, d in atts]

    if level == 4:
        from qumail.crypto import level4
        key = _request(km, level4.KEY_BYTES_NEEDED, "level4")
        prepared = _stamp(envelope.encrypt(4, text, key_material=key.material, key_id=key.key_id), key.material)
        keys = level4.derive_keys(key.material)
        return _encrypted(prepared, 4, len(atts)), [(n + ".qenc", level4.encrypt_bytes(d, keys)) for n, d in atts]

    if level == 3:
        from qumail.crypto import level3
        if hybrid and atts:
            from qumail.crypto import level2
            key = _request(km, level3.key_bytes_needed(len(text.encode()), []), "level3-body")
            prepared, _ = envelope.encrypt(3, text, key_material=key.material, key_id=key.key_id, attachments=[])
            att_key = _request(km, level2.KEY_BYTES_NEEDED, "level3-hybrid-attachments")
            env = json.loads(prepared.body)
            env["att"] = {"level": 2, "key_id": att_key.key_id}
            env["key_fp"] = key_fingerprint(key.material)
            env["att_fp"] = key_fingerprint(att_key.material)
            prepared.body = json.dumps(env, indent=1)
            prepared.extra_key_ids = [att_key.key_id]
            aes = level2.derive_key(att_key.material)
            return _encrypted(prepared, 3, len(atts), hybrid=True), [(n + ".qenc", level2.encrypt_bytes(d, aes)) for n, d in atts]
        need = level3.key_bytes_needed(len(text.encode()), [len(d) for _, d in atts])
        key = _request(km, need, "level3")
        prepared, blobs = envelope.encrypt(3, text, key_material=key.material, key_id=key.key_id, attachments=atts)
        return _encrypted(_stamp(prepared, key.material), 3, len(atts)), blobs

    raise QuMailCryptoError(f"Level {level} not available")


def burn_key(prepared, km: KMClient) -> None:
    """Send failed after a key was reserved: mark it CONSUMED so it is never reused (Day 10)."""
    ids = [getattr(prepared, "key_id", None)] + list(getattr(prepared, "extra_key_ids", []))
    for kid in filter(None, ids):
        try:
            km.consume(kid)
            audit.log("key_burned", key_id=kid, reason="send failed")
        except KMError:
            audit.log("key_burned", key_id=kid, reason="send failed", km_error=True)


def open_message(msg, km: KMClient) -> str | None:
    """Decrypt msg in place (body + attachments). Returns a status note or None for Level 1.

    SCRUM-64: with QUMAIL_CONSUME_AFTER_DECRYPT=1 the key(s) are marked CONSUMED after the
    first successful decrypt, so the mail becomes read-once (true one-time key policy).
    """
    note = _open_message(msg, km)
    if note is not None and get_settings().consume_after_decrypt:
        ids = [msg.key_id] + [a.get("key_id") for a in [_hybrid_att(msg)] if a]
        for kid in filter(None, ids):
            try:
                km.consume(kid)
                audit.log("key_consumed", key_id=kid, reason="read once")
            except KMError:
                pass
        note += " · key consumed (read-once policy)"
    return note


def _hybrid_att(msg) -> dict | None:
    env = envelope.parse_envelope(getattr(msg, "_raw_body", "") or "") or {}
    return env.get("att")


def _open_message(msg, km: KMClient) -> str | None:
    if msg.level < 2:
        return None
    if not msg.key_id:
        raise QuMailCryptoError("Encrypted message has no X-QuMail-KeyID header")
    msg._raw_body = msg.body                                   # kept for the read-once policy (hybrid att key)
    key = km.get_key(msg.key_id)
    audit.log("key_fetched", key_id=msg.key_id, level=msg.level, bytes=len(key.material))
    head = envelope.parse_envelope(msg.body) or {}
    _verify_key(head, msg.key_id, key.material)              # BB-07: wrong KM → clear message, not "Integrity"
    try:
        return _decrypt_with(msg, km, key)
    except KeyMismatch:
        raise
    except QuMailCryptoError as exc:
        if "key_fp" not in head and "Integrity" in str(exc):   # mail from before fingerprints existed
            raise QuMailCryptoError(f"{exc}. Most likely cause: {WRONG_KM_HINT}") from exc
        raise


def _decrypt_with(msg, km: KMClient, key) -> str | None:

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
        env = envelope.parse_envelope(msg.body) or {}
        att_info = env.get("att")
        if att_info:                                   # hybrid: OTP body, AES-GCM attachments (Day 15)
            from qumail.crypto import level2
            msg.body, _ = envelope.decrypt(3, msg.body, key_material=key.material, attachments=[])
            att_key = km.get_key(att_info["key_id"])
            _verify_key(env, att_info["key_id"], att_key.material, field="att_fp")
            aes = level2.derive_key(att_key.material)
            for att in msg.attachments:
                if att.filename.endswith(".qenc"):
                    att.data = level2.decrypt_bytes(att.data, aes)
                    att.filename = att.filename[:-5]
                    att.content_type = mimetypes.guess_type(att.filename)[0] or "application/octet-stream"
            audit.log("mail_decrypted", level=3, key_id=msg.key_id, extra_keys=[att_info["key_id"]], hybrid=True)
            return (f"🔓 Decrypted with quantum key {msg.key_id} (Level 3 body) + {att_info['key_id']} "
                    f"(Level 2 attachments)")
        enc = [(a.filename, a.data) for a in msg.attachments if a.filename.endswith(".qenc")]
        msg.body, plain = envelope.decrypt(3, msg.body, key_material=key.material, attachments=enc)
        by_name = dict(plain)
        for att in msg.attachments:
            if att.filename.endswith(".qenc"):
                att.filename = att.filename[:-5]
                att.data = by_name[att.filename]
                att.content_type = mimetypes.guess_type(att.filename)[0] or "application/octet-stream"
    elif msg.level == 4:
        from qumail.crypto import level4
        msg.body = envelope.decrypt(4, msg.body, key_material=key.material)
        keys = level4.derive_keys(key.material)
        for att in msg.attachments:
            if att.filename.endswith(".qenc"):
                att.data = level4.decrypt_bytes(att.data, keys)
                att.filename = att.filename[:-5]
                att.content_type = mimetypes.guess_type(att.filename)[0] or "application/octet-stream"
        audit.log("mail_decrypted", level=4, key_id=msg.key_id)
        return f"🔓 Decrypted with quantum key {msg.key_id} (Level 4, AES-256-GCM + ChaCha20-Poly1305 double layer)"
    else:
        raise QuMailCryptoError(f"Level {msg.level} not available")
    audit.log("mail_decrypted", level=msg.level, key_id=msg.key_id)
    return f"🔓 Decrypted with quantum key {msg.key_id} (Level {msg.level}, {len(key.material):,} key bytes)"
