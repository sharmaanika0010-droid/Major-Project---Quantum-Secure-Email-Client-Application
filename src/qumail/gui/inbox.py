"""Minimal inbox list (Day 3). Rendering/preview is extended on Day 6."""
from __future__ import annotations

import threading

import customtkinter as ctk

from qumail.email.imap_client import IMAPClient, IMAPError


class InboxFrame(ctk.CTkFrame):
    def __init__(self, master, client: IMAPClient, on_logout):
        super().__init__(master, fg_color="transparent")
        self.client = client

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(top, text=f"Inbox — {client.address}", font=("Segoe UI", 16, "bold")).pack(side="left")
        ctk.CTkButton(top, text="Logout", width=80, command=on_logout).pack(side="right")
        ctk.CTkButton(top, text="Refresh", width=80, command=self.refresh).pack(side="right", padx=6)

        self.status = ctk.CTkLabel(self, text="Loading…", text_color="gray")
        self.status.pack(anchor="w", padx=16)

        self.list = ctk.CTkScrollableFrame(self)
        self.list.pack(fill="both", expand=True, padx=16, pady=10)
        self.refresh()

    def refresh(self):
        for w in self.list.winfo_children():
            w.destroy()
        self.status.configure(text="Loading…")

        def work():
            try:
                items = self.client.fetch_inbox(limit=25)
            except IMAPError as exc:
                self.after(0, lambda: self.status.configure(text=f"Error: {exc}"))
                return
            self.after(0, self._render, items)

        threading.Thread(target=work, daemon=True).start()

    def _render(self, items):
        self.status.configure(text=f"{len(items)} messages (newest first)")
        for m in items:
            row = ctk.CTkFrame(self.list)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=m.sender[:40], width=260, anchor="w",
                         font=("Segoe UI", 12, "bold")).pack(side="left", padx=8)
            ctk.CTkLabel(row, text=m.subject[:70], anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(row, text=m.date[:16], width=130, anchor="e", text_color="gray").pack(side="right", padx=8)
