"""Central configuration for QuMail (SCRUM-56).

Everything that used to be a literal in the code — Key Manager URL, timeouts,
attachment limits, default login values — is read from environment variables
(optionally from a `.env` file in the project root).  Nothing in this file is a
secret, and the e-mail *password* is deliberately NOT configurable here: it is
typed in the login screen and kept only in memory.

    cp .env.example .env     # then edit

Every value has a safe default, so the app runs with no .env at all.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROVIDERS = ("Gmail", "Yahoo")

_ROOT = Path(__file__).resolve().parents[2]      # repo root (…/src/qumail/config.py → …/)


def _env_file() -> Optional[Path]:
    """`.env` next to the project root, or in the current directory."""
    for p in (_ROOT / ".env", Path.cwd() / ".env"):
        if p.is_file():
            return p
    return None


def _int(name: str, default: int, lo: int, hi: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        val = int(raw)
    except ValueError:
        return default
    return default if not lo <= val <= hi else val


def _float(name: str, default: float, lo: float, hi: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        val = float(raw)
    except ValueError:
        return default
    return default if not lo <= val <= hi else val


@dataclass(frozen=True)
class Settings:
    # login screen defaults (never the password)
    email: str = ""
    provider: str = "Gmail"
    # Key Manager
    km_url: str = "http://localhost:5000"
    km_timeout: float = 5.0
    # mail transport
    smtp_port: int = 465
    smtp_timeout: int = 30
    imap_timeout: int = 30
    # attachment limits (see crypto/limits.py)
    max_files: int = 10
    max_file_mb: int = 15
    max_total_mb: int = 18
    level3_warn_kb: int = 50
    # address book (SCRUM-57) — JSON outside the repo
    contacts_file: str = "~/.qumail/contacts.json"
    # where the values came from (for the About / debug output)
    env_file: str = ""

    @classmethod
    def from_env(cls, dotenv: bool = True) -> "Settings":
        env_path = _env_file() if dotenv else None
        if env_path:
            load_dotenv(env_path, override=False)

        provider = os.getenv("QUMAIL_PROVIDER", "Gmail").strip().title()
        if provider not in PROVIDERS:
            provider = "Gmail"

        km_url = os.getenv("QUMAIL_KM_URL", "http://localhost:5000").strip().rstrip("/")
        if not km_url.startswith(("http://", "https://")):
            km_url = "http://localhost:5000"

        return cls(
            email=os.getenv("QUMAIL_EMAIL", "").strip(),
            provider=provider,
            km_url=km_url,
            km_timeout=_float("QUMAIL_KM_TIMEOUT", 5.0, 1, 120),
            smtp_port=_int("QUMAIL_SMTP_PORT", 465, 1, 65535),
            smtp_timeout=_int("QUMAIL_SMTP_TIMEOUT", 30, 5, 600),
            imap_timeout=_int("QUMAIL_IMAP_TIMEOUT", 30, 5, 600),
            max_files=_int("QUMAIL_MAX_FILES", 10, 1, 50),
            max_file_mb=_int("QUMAIL_MAX_FILE_MB", 15, 1, 25),
            max_total_mb=_int("QUMAIL_MAX_TOTAL_MB", 18, 1, 25),
            level3_warn_kb=_int("QUMAIL_LEVEL3_WARN_KB", 50, 1, 1024),
            contacts_file=os.getenv("QUMAIL_CONTACTS_FILE", "~/.qumail/contacts.json").strip() or "~/.qumail/contacts.json",
            env_file=str(env_path) if env_path else "",
        )

    def as_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Settings are loaded once per process; call reload() in tests."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reload(dotenv: bool = True) -> Settings:
    global _settings
    _settings = Settings.from_env(dotenv=dotenv)
    return _settings
