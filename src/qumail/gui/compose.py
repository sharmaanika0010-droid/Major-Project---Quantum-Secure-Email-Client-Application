"""Compose window — Level 1 (Day 7), Level 2 (Day 8), Level 3 OTP + key-length check (Day 9),
key-bank depletion / no-keys error state (Day 10, SCRUM-39).

Security level dropdown lists only the levels registered in qumail.crypto.envelope,
so Levels 2/3/4 appear automatically once their modules register.
"""
from __future__ import annotations

import threading
from tkinter import filedialog

import customtkinter as ctk

from qumail import audit
from qumail.contacts import get_book
from qumail.crypto import envelope, limits, pipeline
from qumail.email.smtp_client import SMTPClient, SMTPError
from qumail.gui.contacts import ContactsWindow
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
        trow = ctk.CTkFrame(self, fg_color="transparent")
        trow.pack(fill="x", padx=16)
        self.to = ctk.CTkEntry(trow, placeholder_text="someone@example.com")
        self.to.pack(side="left", fill="x", expand=True)
        self.to.bind("<FocusOut>", lambda _e: self._apply_contact())
        self.to.bind("<Return>", lambda _e: self._apply_contact())
        ctk.CTkButton(trow, text="📒 Contacts", width=100, fg_color="gray50", command=self._pick_contact).pack(side="left", padx=(6, 0))
        self.contact_lbl = ctk.CTkLabel(self, text="", text_color="gray", anchor="w", font=("Segoe UI", 11))
        self.contact_lbl.pack(fill="x", padx=16)
        self.book = get_book()

        ctk.CTkLabel(self, text="Subject", anchor="w").pack(fill="x", **pad)
        self.subject = ctk.CTkEntry(self)
        self.subject.pack(fill="x", padx=16)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", **pad)
        ctk.CTkLabel(row, text="Security level").pack(side="left")
        levels = envelope.available_levels()
        self._level_by_label = {v: k for k, v in levels.items()}
        self.level = ctk.CTkOptionMenu(row, values=list(levels.values()), width=320, command=self._level_changed)
        self.level.pack(side="left", padx=10)
        self.km_lbl = ctk.CTkLabel(row, text="🔑 checking KM…", text_color="gray", font=("Segoe UI", 11))
        self.km_lbl.pack(side="left", padx=4)
        self.after(50, self._refresh_km)

        # Day 15: extra encryption option for Level 3 — OTP body + AES attachments
        self.hybrid = ctk.BooleanVar(value=False)
        self.hybrid_chk = ctk.CTkCheckBox(self, variable=self.hybrid, font=("Segoe UI", 11),
                                          text="Hybrid: One-Time Pad for the text, AES-256-GCM (Level 2) for attachments "
                                               "— needs only ~1 KB of key per file")
        # packed/unpacked by _level_changed

        ctk.CTkLabel(self, text="Message", anchor="w").pack(fill="x", **pad)
        self.body = ctk.CTkTextbox(self, wrap="word", font=("Segoe UI", 12))
        self.body.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        arow = ctk.CTkFrame(self, fg_color="transparent")
        arow.pack(fill="x", padx=16)
        ctk.CTkButton(arow, text="📎 Attach", width=90, fg_color="gray50", command=self._attach).pack(side="left")
        self.clear_btn = ctk.CTkButton(arow, text="✕ Clear", width=70, fg_color="gray30", command=self._clear_attachments)
        self.attach_lbl = ctk.CTkLabel(arow, text="No attachments", text_color="gray", anchor="w",
                                       wraplength=380, justify="left", font=("Segoe UI", 11))
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

    # -- address book (SCRUM-57) -------------------------------------------
    def _pick_contact(self):
        ContactsWindow(self, self.book, on_pick=self._use_contact)

    def _use_contact(self, contact):
        self.to.delete(0, "end")
        self.to.insert(0, contact.email)
        self._apply_contact()

    def _apply_contact(self):
        """Known recipient → pre-select their preferred level and show key-exchange info."""
        c = self.book.get(self.to.get())
        if not c:
            self.contact_lbl.configure(text="")
            return
        label = next((lbl for lbl, lvl in self._level_by_label.items() if lvl == c.preferred_level), None)
        if label and label in self.level.cget("values"):
            self.level.set(label)
            self._level_changed(label)
        info = f"{c.display} · prefers Level {c.preferred_level}"
        if c.km_peer_id:
            info += f" · KM peer {c.km_peer_id}"
        self.contact_lbl.configure(text=info)

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

    def _level_changed(self, label: str = None):
        lvl = self._level_by_label.get(label or self.level.get(), 1)
        if lvl == 3:
            self.hybrid_chk.pack(fill="x", padx=16, pady=(0, 4), before=self.body)
        else:
            self.hybrid_chk.pack_forget()

    # -- attachments (Day 15: multiple files, size validation) -------------
    def _attach(self):
        paths = filedialog.askopenfilenames(title="Attach files")
        if not paths:
            return
        candidate = list(dict.fromkeys(self.files + list(paths)))   # keep order, drop duplicates
        problem = limits.validate(candidate)
        if problem:
            self.status.configure(text=problem, text_color="#e74c3c")
            return
        self.files = candidate
        self.status.configure(text="")
        self._show_attachments()

    def _clear_attachments(self):
        self.files = []
        self._show_attachments()

    def _show_attachments(self):
        self.attach_lbl.configure(text=limits.summary(self.files), text_color="gray" if not self.files else ("gray85"))
        if self.files:
            self.clear_btn.pack(side="left", padx=(6, 0), before=self.attach_lbl)
        else:
            self.clear_btn.pack_forget()
        total = sum(n for _, n in limits.sizes(self.files))
        if total > limits.LEVEL3_WARN_BYTES and self._level_by_label.get(self.level.get()) == 3 and not self.hybrid.get():
            self.status.configure(text=f"{limits.human(total)} at Level 3 needs that much quantum key — "
                                       "tick 'Hybrid' or use Level 2.", text_color="#f39c12")

    def _send(self):
        to = self.to.get().strip()
        subject = self.subject.get().strip() or "(no subject)"
        text = self.body.get("1.0", "end").strip()
        level = self._level_by_label[self.level.get()]
        hybrid = level == 3 and bool(self.hybrid.get())
        if not to or "@" not in to:
            self.status.configure(text="Enter a valid recipient", text_color="#e74c3c")
            return
        self.send_btn.configure(state="disabled", text="Sending…")
        self.status.configure(text=f"Preparing (Level {level})…", text_color="gray")

        self.fallback_btn.pack_forget()

        def work():
            prepared = None
            try:
                problem = pipeline.check_capacity(level, text, self.files, self.km, hybrid)
                if problem:
                    self.after(0, self._fail, problem, level >= 2)
                    return
                if level >= 2:
                    self.after(0, lambda: self.status.configure(text="Requesting quantum key from KM…"))
                prepared, files = pipeline.prepare(level, text, self.files, self.km, hybrid)
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
        audit.log("mail_sent", to=self.to.get().strip(), level=level, message_id=msg_id, attachments=len(self.files))
        try:
            self.book.remember(self.to.get().strip(), level)    # auto-add recipient, remember level
        except Exception:                                       # noqa: BLE001 — never block the send UI
            pass
        if self.on_sent:
            self.on_sent(msg_id, level)
        self.after(900, self.destroy)
