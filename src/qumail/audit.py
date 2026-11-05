"""Audit trail for quantum-key usage (SCRUM-58).

Every security-relevant event — key requested, key fetched for decryption, key
consumed/burned, mail encrypted / decrypted, login — is appended as one JSON
line to ``~/.qumail/audit.log`` (override with ``QUMAIL_AUDIT_FILE``).

Design rules
* **Never** log key material, passwords or message text.  ``log()`` refuses
  field names that look like secrets, and tests enforce it.
* **Tamper-evident**: each line carries ``prev`` = SHA-256 of the previous line,
  so editing or deleting an entry breaks the chain (``verify()`` detects it).
* **Never crashes the app**: I/O errors are swallowed; the audit log is
  best-effort telemetry, not a transaction log.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_FORBIDDEN = ("material", "password", "secret", "token", "body", "plaintext", "text")
_GENESIS = "0" * 64

logger = logging.getLogger("qumail.audit")


class AuditError(ValueError):
    """A caller tried to log something that must never be persisted."""


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path).expanduser()
        self._lock = threading.Lock()
        self._last_hash: Optional[str] = None

    # -- writing ----------------------------------------------------------------
    def log(self, event: str, **fields: Any) -> Dict[str, Any]:
        for name in fields:
            if any(bad in name.lower() for bad in _FORBIDDEN):
                raise AuditError(f"refusing to log field '{name}' — looks like a secret")
        entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event, **fields}
        with self._lock:
            entry["prev"] = self._tail_hash()
            line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                self._last_hash = _h(line)
            except OSError as exc:                       # never break the GUI because of the log
                logger.warning("audit log write failed: %s", exc)
        logger.info("%s %s", event, {k: v for k, v in fields.items()})
        return entry

    def _tail_hash(self) -> str:
        if self._last_hash is not None:
            return self._last_hash
        lines = self._lines()
        self._last_hash = _h(lines[-1]) if lines else _GENESIS
        return self._last_hash

    # -- reading ----------------------------------------------------------------
    def _lines(self) -> List[str]:
        try:
            return [ln for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        except OSError:
            return []

    def entries(self) -> List[Dict[str, Any]]:
        out = []
        for ln in self._lines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                out.append({"event": "corrupt_line", "raw": ln})
        return out

    def tail(self, n: int = 200) -> List[Dict[str, Any]]:
        return self.entries()[-n:]

    def verify(self) -> tuple[bool, int]:
        """Walk the hash chain. Returns (ok, index_of_first_bad_line or -1)."""
        prev = _GENESIS
        for i, ln in enumerate(self._lines()):
            try:
                if json.loads(ln).get("prev") != prev:
                    return False, i
            except ValueError:
                return False, i
            prev = _h(ln)
        return True, -1

    def key_summary(self) -> Dict[str, int]:
        """Counts per key-related event — used by the Audit window and reports."""
        counts: Dict[str, int] = {}
        for e in self.entries():
            counts[e.get("event", "?")] = counts.get(e.get("event", "?"), 0) + 1
        return counts


def _h(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


_log: Optional[AuditLog] = None


def get_audit() -> AuditLog:
    global _log
    if _log is None:
        from qumail.config import get_settings
        _log = AuditLog(Path(get_settings().audit_file))
    return _log


def log(event: str, **fields: Any) -> None:
    """Module-level shortcut used by pipeline / KM client / GUI."""
    try:
        get_audit().log(event, **fields)
    except AuditError:
        raise
    except Exception as exc:                              # noqa: BLE001
        logger.warning("audit unavailable: %s", exc)
