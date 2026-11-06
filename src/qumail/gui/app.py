"""QuMail entry point:  python -m qumail.gui.app"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

import customtkinter as ctk

from qumail import km_launcher
from qumail.config import get_settings
from qumail.crypto import envelope
from qumail.gui.inbox import InboxFrame
from qumail.gui.login import LoginFrame
from qumail.gui.ui import enable_windows_dpi

envelope.load_levels()  # registers Level 2 (+3/4 when present)
get_settings()          # reads .env once (SCRUM-56); password is never read from config
enable_windows_dpi()    # SCRUM-60: crisp text on scaled Windows displays


def _icon_path() -> Path | None:
    """qumail.ico shipped next to the exe (PyInstaller) or in packaging/ during development."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3] / "packaging"
    for cand in (base / "qumail.ico", Path(getattr(sys, "_MEIPASS", "")) / "qumail.ico"):
        if cand.is_file():
            return cand
    return None


class QuMailApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QuMail — Quantum Secure Email")
        self.geometry("1000x680")
        self.minsize(760, 600)
        ico = _icon_path()
        if ico and sys.platform == "win32":
            with contextlib.suppress(Exception):                # cosmetic only
                self.iconbitmap(str(ico))
        self.protocol("WM_DELETE_WINDOW", self._quit)
        # Desktop-app behaviour: bring up the local Key Manager automatically (no console needed)
        self.after(100, lambda: km_launcher.ensure_running(get_settings().km_url))
        self.current = None
        self.client = None
        self.smtp = None
        self.show_login()

    def _quit(self):
        km_launcher.stop()                                      # only stops a KM we started ourselves
        self.destroy()

    def _swap(self, frame):
        if self.current is not None:
            self.current.destroy()
        self.current = frame
        frame.pack(fill="both", expand=True)

    def show_login(self):
        if self.client:
            self.client.close()
            self.client = None
        self._swap(LoginFrame(self, on_success=self.show_inbox))

    def show_inbox(self, client, smtp, km):
        self.client = client
        self.smtp = smtp
        self.km = km
        inbox = InboxFrame(self, client, smtp, km, on_logout=self.show_login)
        self._swap(inbox)
        # SCRUM-60 keyboard shortcuts (Windows conventions)
        self.bind("<Control-n>", lambda _e: inbox.compose())
        self.bind("<F5>", lambda _e: inbox.refresh())
        self.bind("<Control-l>", lambda _e: self.show_login())


if __name__ == "__main__":
    QuMailApp().mainloop()
