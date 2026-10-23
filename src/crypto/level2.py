"""SCRUM-23 | Level 2 send/receive glue: Key Manager + AES module + email provider.

Ticket: SCRUM-23
Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com

Send:    request key (RESERVED) -> encrypt body + attachments -> send. Fails closed:
         if the KM or encryption fails nothing is sent.
Receive: read Key-ID from envelope -> GET key from KM -> decrypt -> mark CONSUMED.
Simulation note: sender and receiver share one KM bank, so the key is consumed by the
receiver after a successful decrypt (consuming at send time would make GET /keys/{id}
return 410 for the receiver).
"""
import base64
import json
import mimetypes
import os
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import aes

ENC_SUFFIX = ".qumail"
KEY_BYTES_NEEDED = aes.MIN_KEY_MATERIAL  # 32 B -> KM rounds up to one 1 KB key


class KMError(Exception):
    """Key Manager unreachable or returned an error."""


class KMClient:
    """Thin client for the SCRUM-14 KM simulator (keeps KM replaceable)."""

    def __init__(self, base_url: str = "http://127.0.0.1:5000", timeout: float = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _call(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read()).get("detail", "")
            except Exception:
                detail = ""
            raise KMError(f"KM error {e.code}: {detail}") from None
        except (urllib.error.URLError, OSError) as e:
            raise KMError(f"Key Manager unreachable: {e}") from None

    def request_key(self, nbytes: int = KEY_BYTES_NEEDED) -> Tuple[str, bytes]:
        r = self._call("POST", "/keys/request", {"key_bytes": nbytes})
        if len(r["key_ids"]) != 1:
            raise KMError("expected exactly one key block for Level 2")
        return r["key_ids"][0], base64.b64decode(r["key_material"])

    def fetch_key(self, key_id: str) -> bytes:
        r = self._call("GET", f"/keys/{key_id}")
        return base64.b64decode(r["key_material"])

    def consume(self, key_id: str) -> None:
        self._call("POST", "/keys/consume", {"key_ids": [key_id]})


@dataclass
class DecryptedMessage:
    key_id: str
    body: str
    attachments: List[Tuple[str, bytes]] = field(default_factory=list)  # (filename, bytes)


def send_level2(provider, km, to: str, subject: str, body: str,
                attachment_paths: Optional[List[str]] = None) -> Tuple[str, str]:
    """Encrypt and send. Returns (message_id, key_id). Subject stays in clear."""
    key_id, material = km.request_key()
    body_env = aes.encrypt(body.encode("utf-8"), material, key_id, "text/plain")
    with tempfile.TemporaryDirectory() as tmp:
        enc_paths = []
        for path in attachment_paths or []:
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            with open(path, "rb") as f:
                env = aes.encrypt(f.read(), material, key_id, ctype)
            out = os.path.join(tmp, os.path.basename(path) + ENC_SUFFIX)
            with open(out, "w", newline="\n") as f:
                f.write(env)
            enc_paths.append(out)
        msg_id = provider.send_message(to, subject, body_env, enc_paths)
    return msg_id, key_id


def is_qumail_message(msg) -> bool:
    return aes.is_envelope(getattr(msg, "body", "") or "")


def read_level2(provider, km, msg) -> DecryptedMessage:
    """Decrypt a received QuMail Level 2 message, then mark its key CONSUMED."""
    env = aes.parse_envelope(msg.body)
    material = km.fetch_key(env.key_id)
    body = aes.decrypt_envelope(env, material).decode("utf-8")
    files = []
    for att in msg.attachments:
        if not att.filename.endswith(ENC_SUFFIX):
            continue
        raw = att.data
        if not raw:
            raw = provider.download_attachment(msg.message_id, att.attachment_id)
        a_env = aes.parse_envelope(raw.decode("utf-8"))
        if a_env.key_id != env.key_id:
            raise aes.QuMailCryptoError("attachment was encrypted with a different key")
        files.append((att.filename[:-len(ENC_SUFFIX)], aes.decrypt_envelope(a_env, material)))
    km.consume(env.key_id)
    return DecryptedMessage(env.key_id, body, files)
