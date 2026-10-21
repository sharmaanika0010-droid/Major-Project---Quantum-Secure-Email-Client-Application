"""Compose window — Level 1 (Day 7), Level 2 (Day 8), Level 3 OTP + key-length check (Day 9),
key-bank depletion / no-keys error state (Day 10, SCRUM-39).

Security level dropdown lists only the levels registered in qumail.crypto.envelope,
so Levels 2/3/4 appear automatically once their modules register.
"""
from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from qumail.crypto import envelope, pipeline
from qumail.email.smtp_client import SMTPClient, SMTPError
from qumail.km.client import KMClient, KMError, KMUnreachable, NoKeysAvailable


class ComposeWindow(ctk.CTkToplevel):
    def __init__(self, master, smtp: SMTPClient, km: KMClient, on_sent=None):
        super().__init__(master)
        self.smtp = smtp
        self.km = km
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
        self.km_lbl = ctk.CTkLabel(row, text="🔑 checking KM…", text_color="gray", font=("Segoe UI", 11))
        self.km_lbl.pack(side="left", padx=4)
        self.after(50, self._refresh_km)

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
        self.status = ctk.CTkLabel(brow, text="", text_color="gray", anchor="w", wraplength=380, justify="left")
        self.status.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(brow, text="Cancel", width=80, fg_color="gray50", command=self.destroy).pack(side="right", padx=(6, 0))
        self.send_btn = ctk.CTkButton(brow, text="Send", width=100, command=self._send)
        self.send_btn.pack(side="right")
        self.fallback_btn = ctk.CTkButton(brow, text="Send as Level 1 instead", width=170, fg_color="#e67e22",
                                          hover_color="#d35400", command=self._fallback_level1)
        # shown only in the no-keys error state

    # -- KM key-bank state (Day 10) ----------------------------------------
    def _refresh_km(self):
        def work():
            try:
                st = self.km.status()
                avail = int(st.get("available", 0))
                self.after(0, self._apply_km_state, avail, None)
            except KMError as exc:
                self.after(0, self._apply_km_state, None, str(exc))
        threading.Thread(target=work, daemon=True).start()

    def _apply_km_state(self, available, error):
        plain_only = [lbl for lbl, lvl in self._level_by_label.items() if lvl == 1]
        all_levels = list(self._level_by_label.keys())
        if error is not None:
            self.km_lbl.configure(text="🔑 KM offline — only Level 1", text_color="#e74c3c")
            self.level.configure(values=plain_only)
            self.level.set(plain_only[0])
        elif available == 0:
            self.km_lbl.configure(text="🔑 Key bank EMPTY — only Level 1", text_color="#e74c3c")
            self.level.configure(values=plain_only)
            self.level.set(plain_only[0])
        elif available <= 10:
            self.km_lbl.configure(text=f"🔑 {available} keys left (low)", text_color="#f39c12")
            self.level.configure(values=all_levels)
        else:
            self.km_lbl.configure(text=f"🔑 {available} quantum keys available", text_color="#2ecc71")
            self.level.configure(values=all_levels)

    def _fallback_level1(self):
        plain = [lbl for lbl, lvl in self._level_by_label.items() if lvl == 1][0]
        self.level.set(plain)
        self.fallback_btn.pack_forget()
        self._send()

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

        self.fallback_btn.pack_forget()

        def work():
            prepared = None
            try:
                problem = pipeline.check_capacity(level, text, self.files, self.km)
                if problem:
                    self.after(0, self._fail, problem, level >= 2)
                    return
                if level >= 2:
                    self.after(0, lambda: self.status.configure(text="Requesting quantum key from KM…"))
                prepared, files = pipeline.prepare(level, text, self.files, self.km)
                self.after(0, lambda: self.status.configure(text="Sending…"))
                msg_id = self.smtp.send(to, subject, prepared.body, prepared.headers(), files)
            except (NoKeysAvailable, KMUnreachable) as exc:
                self.after(0, self._fail, str(exc), True)       # offer Level 1 fallback
                return
            except (envelope.QuMailCryptoError, SMTPError, KMError, OSError) as exc:
                if prepared is not None and level >= 2:
                    pipeline.burn_key(prepared, self.km)        # never reuse a key from a failed send
                self.after(0, self._fail, f"{exc} (reserved key {getattr(prepared, 'key_id', '')} discarded)" if prepared else str(exc))
                return
            self.after(0, self._ok, msg_id, level)

        threading.Thread(target=work, daemon=True).start()

    def _fail(self, message: str, offer_plain: bool = False):
        self.send_btn.configure(state="normal", text="Send")
        self.status.configure(text=message, text_color="#e74c3c")
        self._refresh_km()
        if offer_plain:
            self.fallback_btn.pack(side="right", padx=(0, 6))

    def _ok(self, msg_id: str, level: int):
        self.status.configure(text=f"Sent (Level {level})", text_color="#2ecc71")
        if self.on_sent:
            self.on_sent(msg_id, level)
        self.after(900, self.destroy)
