"""Audit-trail window (SCRUM-58): last entries, per-event counts, chain verification."""
from __future__ import annotations

import customtkinter as ctk

from qumail.audit import AuditLog

_ICON = {"key_requested": "🔑", "key_fetched": "🔎", "key_consumed": "🔥", "key_burned": "🔥",
         "mail_encrypted": "🔒", "mail_sent": "✉", "mail_decrypted": "🔓", "decrypt_failed": "⛔", "login": "👤"}


class AuditWindow(ctk.CTkToplevel):
    def __init__(self, master, audit: AuditLog):
        super().__init__(master)
        self.audit = audit
        self.title("QuMail — Key usage audit trail")
        self.geometry("820x480")
        self.after(100, self.lift)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(top, text="Key usage audit trail", font=("Segoe UI", 16, "bold")).pack(side="left")
        ctk.CTkButton(top, text="Refresh", width=80, command=self._render).pack(side="right")
        self.chain = ctk.CTkLabel(top, text="", font=("Segoe UI", 12))
        self.chain.pack(side="right", padx=10)
        self.path_lbl = ctk.CTkLabel(self, text=str(audit.path), text_color="gray", font=("Segoe UI", 11), anchor="w")
        self.path_lbl.pack(fill="x", padx=16)
        self.summary = ctk.CTkLabel(self, text="", text_color="gray", anchor="w", font=("Segoe UI", 11))
        self.summary.pack(fill="x", padx=16, pady=(2, 6))
        self.box = ctk.CTkTextbox(self, font=("Consolas", 11), wrap="none")
        self.box.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self._render()

    def _render(self):
        ok, bad = self.audit.verify()
        self.chain.configure(text="● chain verified" if ok else f"● chain BROKEN at line {bad + 1}",
                             text_color="#2ecc71" if ok else "#e74c3c")
        counts = self.audit.key_summary()
        self.summary.configure(text="   ".join(f"{_ICON.get(k, '•')} {k}: {v}" for k, v in sorted(counts.items())) or "no events yet")
        self.box.configure(state="normal")
        self.box.delete("1.0", "end")
        for e in reversed(self.audit.tail(300)):
            ts = e.get("ts", "")[:19].replace("T", " ")
            ev = e.get("event", "?")
            rest = "  ".join(f"{k}={v}" for k, v in e.items() if k not in ("ts", "event", "prev"))
            self.box.insert("end", f"{ts}  {_ICON.get(ev, '•')} {ev:<15} {rest}\n")
        self.box.configure(state="disabled")
