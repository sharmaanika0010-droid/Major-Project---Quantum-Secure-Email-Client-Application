"""Small UI helpers shared by all windows (SCRUM-60, Windows cleanup pass).

* ``enable_windows_dpi()``  – crisp text on high-DPI / scaled Windows displays.
* ``center_on_parent()``    – dialogs open over the main window instead of at (0,0).
* ``bind_dialog_keys()``    – Esc closes a dialog, optional Ctrl+Enter = primary action.
* ``friendly_date()``       – "04 Nov 2026 22:04" instead of raw RFC-2822 header text.
* ``friendly_sender()``     – "Anika Sharma" instead of "Anika Sharma <sharmaanika0010@gmail.com>".
* ``FONT`` / ``FONT_BOLD`` / ``FONT_SMALL`` / ``FONT_MONO`` – one place for font choices.
"""
from __future__ import annotations

import contextlib
import sys
from email.utils import parseaddr, parsedate_to_datetime

FONT = ("Segoe UI", 12)
FONT_SMALL = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 12, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_MONO = ("Consolas", 11)

BTN_PRIMARY = {"fg_color": "#2ecc71", "hover_color": "#27ae60", "text_color": "black"}
BTN_SECONDARY = {"fg_color": "gray50", "hover_color": "gray40"}
BTN_DANGER = {"fg_color": "#c0392b", "hover_color": "#962d22"}


def enable_windows_dpi() -> None:
    """Tell Windows the process is DPI-aware so Tk does not render blurry on 125 %/150 % scaling."""
    if sys.platform != "win32":
        return
    import ctypes
    with contextlib.suppress(AttributeError, OSError):          # cosmetic only — never fail startup
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)      # Windows 8.1+
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()           # Vista/7 fallback


def center_on_parent(win, parent, width: int, height: int) -> None:
    """Place a Toplevel centred over its parent (clamped to the screen)."""
    try:
        parent.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x = max(0, min(px + (pw - width) // 2, sw - width))
        y = max(0, min(py + (ph - height) // 2, sh - height))
        win.geometry(f"{width}x{height}+{x}+{y}")
    except Exception:                                           # noqa: BLE001 — fall back to default placement
        win.geometry(f"{width}x{height}")


def bind_dialog_keys(win, on_close, on_primary=None) -> None:
    win.bind("<Escape>", lambda _e: on_close())
    if on_primary is not None:
        win.bind("<Control-Return>", lambda _e: on_primary())


def friendly_date(raw: str, with_time: bool = True) -> str:
    """RFC-2822 'Mon, 02 Nov 2026 22:04:54 +0530' → '02 Nov 2026 22:04' (local time)."""
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%d %b %Y %H:%M" if with_time else "%d %b %Y")
    except (TypeError, ValueError, IndexError):
        return raw[:16]


def friendly_sender(raw: str) -> str:
    """'Anika Sharma <a@b.com>' → 'Anika Sharma';  '<a@b.com>' or 'a@b.com' → 'a@b.com'."""
    name, addr = parseaddr(raw or "")
    return (name or addr or raw or "").strip().strip('"')


def ellipsize(text: str, limit: int) -> str:
    """Truncate overflowing list labels using a visible ellipsis (bug bash BB-04)."""
    text = (text or "").strip()
    return text if len(text) <= limit else text[: max(1, limit - 1)].rstrip() + "…"


def parse_recipients(raw: str) -> list[str]:
    """'a@x.com, b@y.com; c@z.com' → ['a@x.com', 'b@y.com', 'c@z.com'] (bug bash BB-03).

    Returns [] when any entry is not a plausible address, so the caller can refuse the send.
    """
    parts = [p.strip() for p in (raw or "").replace(";", ",").split(",")]
    parts = [p for p in parts if p]
    if not parts or any("@" not in p or p.startswith("@") or p.endswith("@") or " " in p for p in parts):
        return []
    return list(dict.fromkeys(parts))
