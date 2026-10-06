"""QuMail entry point:  python -m qumail.gui.app"""
from __future__ import annotations

import customtkinter as ctk
from dotenv import load_dotenv

from qumail.gui.inbox import InboxFrame
from qumail.gui.login import LoginFrame

load_dotenv()  # optional .env with QUMAIL_EMAIL / QUMAIL_KM_URL (never commit .env)


class QuMailApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QuMail — Quantum Secure Email")
        self.geometry("760x620")
        self.minsize(560, 560)
        self.current = None
        self.client = None
        self.smtp = None
        self.show_login()

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

    def show_inbox(self, client, smtp):
        self.client = client
        self.smtp = smtp
        self._swap(InboxFrame(self, client, smtp, on_logout=self.show_login))


if __name__ == "__main__":
    QuMailApp().mainloop()
