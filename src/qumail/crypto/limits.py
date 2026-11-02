"""Attachment limits + size validation (SCRUM-54, Day 15).

Gmail/Yahoo reject mails above ~25 MB after MIME base64 overhead (+33 %), so the raw
budget is ~18 MB. We validate before touching the KM so no key is wasted on a mail the
provider would bounce anyway.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

MAX_FILES = 10
MAX_FILE_BYTES = 15 * 1024 * 1024        # per attachment
MAX_TOTAL_BYTES = 18 * 1024 * 1024       # all attachments together (≈ 25 MB after base64)
LEVEL3_WARN_BYTES = 50 * 1024            # above this, OTP is impractical with a 100 KB key bank


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def sizes(paths: Iterable[str]) -> List[Tuple[str, int]]:
    return [(Path(p).name, Path(p).stat().st_size) for p in paths]


def validate(paths: Iterable[str]) -> str | None:
    """Return a human-readable problem, or None if the attachment set is acceptable."""
    paths = list(paths)
    if len(paths) != len(set(paths)):
        return "The same file is attached twice."
    if len(paths) > MAX_FILES:
        return f"Too many attachments: {len(paths)} (max {MAX_FILES})."
    total = 0
    for p in paths:
        f = Path(p)
        if not f.is_file():
            return f"Cannot read '{f.name}'."
        n = f.stat().st_size
        if n == 0:
            return f"'{f.name}' is empty."
        if n > MAX_FILE_BYTES:
            return f"'{f.name}' is {human(n)} — max {human(MAX_FILE_BYTES)} per file."
        total += n
    if total > MAX_TOTAL_BYTES:
        return f"Attachments total {human(total)} — max {human(MAX_TOTAL_BYTES)} per mail (provider limit)."
    return None


def summary(paths: Iterable[str]) -> str:
    s = sizes(paths)
    if not s:
        return "No attachments"
    total = sum(n for _, n in s)
    names = ", ".join(f"{n} ({human(b)})" for n, b in s)
    return f"{len(s)} file{'s' if len(s) > 1 else ''}, {human(total)} — {names}"
