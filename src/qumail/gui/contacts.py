"""Address-book window (SCRUM-57) — list on the left, edit form on the right."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from qumail.contacts import Contact, ContactBook, ContactError
from qumail.gui.ui import bind_dialog_keys, center_on_parent

LEVEL_LABELS = {1: "1 — Plain", 2: "2 — AES-256-GCM", 3: "3 — One-Time Pad", 4: "4 — Double layer"}


class ContactsWindow(ctk.CTkToplevel):
    """on_pick(contact) is set when opened from Compose: a 'Use' button fills the To field."""

    def __init__(self, master, book: ContactBook, on_pick: Optional[Callable[[Contact], None]] = None):
        super().__init__(master)
        self.book = book
        self.on_pick = on_pick
        self.selected: Optional[Contact] = None
        self.title("QuMail — Contacts")
        center_on_parent(self, master.winfo_toplevel(), 760, 480)
        self.minsize(620, 400)
        bind_dialog_keys(self, self.destroy, on_primary=self._save)
        self.after(100, self.lift)

        self.grid_columnconfigure(0, weight=1, minsize=280)
        self.grid_columnconfigure(1, weight=1, minsize=300)
        self.grid_rowconfigure(1, weight=1)

        # -- left: search + list -------------------------------------------
        self.search = ctk.CTkEntry(self, placeholder_text="Search name or e-mail")
        self.search.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=(16, 6))
        self.search.bind("<KeyRelease>", lambda _e: self._render())
        self.list = ctk.CTkScrollableFrame(self, label_text="Contacts")
        self.list.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=(0, 16))

        # -- right: form -----------------------------------------------------
        form = ctk.CTkFrame(self)
        form.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 16), pady=16)
        pad = {"padx": 14, "pady": (8, 0)}
        self.f_title = ctk.CTkLabel(form, text="New contact", font=("Segoe UI", 15, "bold"), anchor="w")
        self.f_title.pack(fill="x", **pad)
        ctk.CTkLabel(form, text="Name", anchor="w").pack(fill="x", **pad)
        self.f_name = ctk.CTkEntry(form)
        self.f_name.pack(fill="x", padx=14)
        ctk.CTkLabel(form, text="E-mail", anchor="w").pack(fill="x", **pad)
        self.f_email = ctk.CTkEntry(form)
        self.f_email.pack(fill="x", padx=14)
        ctk.CTkLabel(form, text="Preferred security level", anchor="w").pack(fill="x", **pad)
        self.f_level = ctk.CTkOptionMenu(form, values=list(LEVEL_LABELS.values()))
        self.f_level.set(LEVEL_LABELS[2])
        self.f_level.pack(fill="x", padx=14)
        ctk.CTkLabel(form, text="Key-Manager peer id (optional)", anchor="w").pack(fill="x", **pad)
        self.f_peer = ctk.CTkEntry(form, placeholder_text="e.g. SAE-amit-01")
        self.f_peer.pack(fill="x", padx=14)
        ctk.CTkLabel(form, text="Notes", anchor="w").pack(fill="x", **pad)
        self.f_notes = ctk.CTkEntry(form, placeholder_text="shares the lab KM with us…")
        self.f_notes.pack(fill="x", padx=14)
        self.f_stats = ctk.CTkLabel(form, text="", text_color="gray", anchor="w", font=("Segoe UI", 11))
        self.f_stats.pack(fill="x", **pad)
        self.f_error = ctk.CTkLabel(form, text="", text_color="#e74c3c", anchor="w", wraplength=280, justify="left")
        self.f_error.pack(fill="x", padx=14)

        brow = ctk.CTkFrame(form, fg_color="transparent")
        brow.pack(fill="x", padx=14, pady=12, side="bottom")
        ctk.CTkButton(brow, text="Save", width=80, command=self._save).pack(side="left")
        ctk.CTkButton(brow, text="New", width=70, fg_color="gray50", command=self._new).pack(side="left", padx=6)
        self.del_btn = ctk.CTkButton(brow, text="Delete", width=80, fg_color="#c0392b", hover_color="#962d22", command=self._delete)
        if on_pick:
            self.use_btn = ctk.CTkButton(brow, text="Use in mail", width=110, fg_color="#2ecc71", hover_color="#27ae60",
                                         text_color="black", command=self._use)
        self._render()

    # -- helpers --------------------------------------------------------------
    def _render(self):
        for w in self.list.winfo_children():
            w.destroy()
        items = self.book.search(self.search.get())
        if not items:
            ctk.CTkLabel(self.list, text="No contacts yet — add one on the right.", text_color="gray").pack(pady=20)
        for c in items:
            row = ctk.CTkButton(self.list, anchor="w", fg_color="transparent", hover_color=("gray80", "gray25"),
                                text=f"{c.name or '—'}\n{c.email}   ·   L{c.preferred_level}",
                                font=("Segoe UI", 12), command=lambda c=c: self._select(c))
            row.pack(fill="x", pady=2)

    def _select(self, c: Contact):
        self.selected = c
        self.f_title.configure(text=c.display)
        for entry, val in ((self.f_name, c.name), (self.f_email, c.email), (self.f_peer, c.km_peer_id), (self.f_notes, c.notes)):
            entry.delete(0, "end")
            entry.insert(0, val)
        self.f_level.set(LEVEL_LABELS.get(c.preferred_level, LEVEL_LABELS[2]))
        self.f_stats.configure(text=f"{c.mails_sent} mail(s) sent" if c.mails_sent else "never mailed")
        self.f_error.configure(text="")
        self.del_btn.pack(side="right")
        if self.on_pick:
            self.use_btn.pack(side="right", padx=(0, 6))

    def _new(self):
        self.selected = None
        self.f_title.configure(text="New contact")
        for entry in (self.f_name, self.f_email, self.f_peer, self.f_notes):
            entry.delete(0, "end")
        self.f_level.set(LEVEL_LABELS[2])
        self.f_stats.configure(text="")
        self.f_error.configure(text="")
        self.del_btn.pack_forget()
        if self.on_pick:
            self.use_btn.pack_forget()

    def _form_contact(self) -> Contact:
        level = next(k for k, v in LEVEL_LABELS.items() if v == self.f_level.get())
        return Contact(email=self.f_email.get(), name=self.f_name.get(), preferred_level=level,
                       km_peer_id=self.f_peer.get(), notes=self.f_notes.get())

    def _save(self):
        try:
            c = self._form_contact()
        except ContactError as exc:
            self.f_error.configure(text=str(exc))
            return
        if self.selected and self.selected.email != c.email:
            self.book.remove(self.selected.email)           # e-mail edited → replace the old entry
        self.book.upsert(c)
        self._select(c)
        self._render()

    def _delete(self):
        if self.selected:
            self.book.remove(self.selected.email)
            self._new()
            self._render()

    def _use(self):
        if self.selected and self.on_pick:
            self.on_pick(self.selected)
            self.destroy()
