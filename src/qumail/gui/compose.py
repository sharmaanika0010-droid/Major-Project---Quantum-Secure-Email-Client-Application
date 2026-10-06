"""Compose window — SCRUM-28 (Day 7): Level 1 send wired end-to-end.

Security level dropdown lists only the levels registered in qumail.crypto.envelope,
so Levels 2/3/4 appear automatically once their modules register.
"""
from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from qumail.crypto import envelope
from qumail.email.smtp_client import SMTPClient, SMTPError


class ComposeWindow(ctk.CTkToplevel):
    def __init__(self, master, smtp: SMTPClient, on_sent=None):
        super().__init__(master)
        self.smtp = smtp
        self.on_sent = on_sent
        self.files: list[str] = []
        self.title("QuMail — New message")
        self.geometry("640x560")
        self.minsize(520, 480)
        self.after(100, self.lift)

        pad = {"padx": 16, "pady": (8, 0)}
        ctk.CTkLabel(self, text="To", anchor="w").pack(fill="x", **pad)
        self.to = ctk.CTkEntry(self, placeholder_text="someone@example.com")
        self.to.pack(fill="x", padx=16)

        ctk.CTkLabel(self, text="Subject", anchor="w").pack(fill="x", **pad)
        self.subject = ctk.CTkEntry(self)
        self.subject.pack(fill="x", padx=16)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", **pad)
        ctk.CTkLabel(row, text="Security level").pack(side="left")
        levels = envelope.available_levels()
        self._level_by_label = {v: k for k, v in levels.items()}
        self.level = ctk.CTkOptionMenu(row, values=list(levels.values()), width=320)
        self.level.pack(side="left", padx=10)

        ctk.CTkLabel(self, text="Message", anchor="w").pack(fill="x", **pad)
        self.body = ctk.CTkTextbox(self, wrap="word", font=("Segoe UI", 12))
        self.body.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        arow = ctk.CTkFrame(self, fg_color="transparent")
        arow.pack(fill="x", padx=16)
        ctk.CTkButton(arow, text="📎 Attach", width=90, fg_color="gray50", command=self._attach).pack(side="left")
        self.attach_lbl = ctk.CTkLabel(arow, text="No attachments", text_color="gray", anchor="w")
        self.attach_lbl.pack(side="left", padx=10, fill="x", expand=True)

        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x", padx=16, pady=12)
        self.status = ctk.CTkLabel(brow, text="", text_color="gray", anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(brow, text="Cancel", width=80, fg_color="gray50", command=self.destroy).pack(side="right", padx=(6, 0))
        self.send_btn = ctk.CTkButton(brow, text="Send", width=100, command=self._send)
        self.send_btn.pack(side="right")

    def _attach(self):
        paths = filedialog.askopenfilenames(title="Attach files")
        if paths:
            self.files.extend(paths)
            self.attach_lbl.configure(text=", ".join(Path(p).name for p in self.files)[:80])

    def _send(self):
        to = self.to.get().strip()
        subject = self.subject.get().strip() or "(no subject)"
        text = self.body.get("1.0", "end").strip()
        level = self._level_by_label[self.level.get()]
        if not to or "@" not in to:
            self.status.configure(text="Enter a valid recipient", text_color="#e74c3c")
            return
        self.send_btn.configure(state="disabled", text="Sending…")
        self.status.configure(text=f"Preparing (Level {level})…", text_color="gray")

        def work():
            try:
                prepared = envelope.encrypt(level, text)
                msg_id = self.smtp.send(to, subject, prepared.body, prepared.headers(), self.files)
            except (envelope.QuMailCryptoError, SMTPError, OSError) as exc:
                self.after(0, self._fail, str(exc))
                return
            self.after(0, self._ok, msg_id, level)

        threading.Thread(target=work, daemon=True).start()

    def _fail(self, message: str):
        self.send_btn.configure(state="normal", text="Send")
        self.status.configure(text=message, text_color="#e74c3c")

    def _ok(self, msg_id: str, level: int):
        self.status.configure(text=f"Sent (Level {level})", text_color="#2ecc71")
        if self.on_sent:
            self.on_sent(msg_id, level)
        self.after(900, self.destroy)
