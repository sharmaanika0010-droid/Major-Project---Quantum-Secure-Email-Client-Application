"""Inbox: message list (left) + reader pane with body and attachments (right).

SCRUM-16 (Day 3): list of newest messages.
SCRUM-24 (Day 6): inbox rendering, attachment download + preview.
Decrypt button is wired on Day 7+ (crypto modules by Umang).
"""
from __future__ import annotations

import io
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk

from qumail.email.imap_client import Attachment, EmailMessage, IMAPClient, IMAPError

LEVEL_COLORS = {1: ("gray70", "gray40"), 2: "#2e86de", 3: "#8e44ad", 4: "#c0392b"}
LEVEL_NAMES = {1: "Plain", 2: "L2 · Quantum AES", 3: "L3 · One-Time Pad", 4: "L4 · Extra"}
PREVIEW_TEXT_TYPES = ("text/plain", "text/csv", "text/markdown", "application/json")
PREVIEW_IMAGE_TYPES = ("image/png", "image/jpeg", "image/gif", "image/bmp", "image/webp")


class InboxFrame(ctk.CTkFrame):
    def __init__(self, master, client: IMAPClient, on_logout):
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.current: EmailMessage | None = None

        # -- top bar ----------------------------------------------------
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(top, text=f"Inbox — {client.address}", font=("Segoe UI", 16, "bold")).pack(side="left")
        ctk.CTkButton(top, text="Logout", width=80, command=on_logout).pack(side="right")
        ctk.CTkButton(top, text="Refresh", width=80, command=self.refresh).pack(side="right", padx=6)
        self.status = ctk.CTkLabel(self, text="Loading…", text_color="gray")
        self.status.pack(anchor="w", padx=16)

        # -- two panes --------------------------------------------------
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=10)
        body.grid_columnconfigure(0, weight=2, minsize=300)
        body.grid_columnconfigure(1, weight=3, minsize=340)
        body.grid_rowconfigure(0, weight=1)

        self.list = ctk.CTkScrollableFrame(body, label_text="Messages")
        self.list.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.reader = ctk.CTkFrame(body)
        self.reader.grid(row=0, column=1, sticky="nsew")
        self._build_reader()
        self.refresh()

    # ------------------------------------------------------------------
    # message list
    # ------------------------------------------------------------------
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
            self.after(0, self._render_list, items)

        threading.Thread(target=work, daemon=True).start()

    def _render_list(self, items):
        self.status.configure(text=f"{len(items)} messages (newest first) — click a message to read it")
        for m in items:
            row = ctk.CTkButton(
                self.list, anchor="w", height=52, corner_radius=6,
                fg_color=("gray90", "gray20"), hover_color=("gray80", "gray30"),
                text_color=("black", "white"),
                text=f"{m.sender[:34]}\n{m.subject[:46]}",
                font=("Segoe UI", 12),
                command=lambda uid=m.uid: self.open_message(uid),
            )
            row.pack(fill="x", pady=2)
            badge = f"L{m.level}" if m.level > 1 else ""
            if m.has_attachments:
                badge = ("📎 " + badge).strip()
            if badge:
                ctk.CTkLabel(row, text=badge, width=44, height=20, corner_radius=10, font=("Segoe UI", 10, "bold"),
                             fg_color=LEVEL_COLORS.get(m.level, "gray"), text_color="white").place(relx=1.0, x=-8, y=6, anchor="ne")
            ctk.CTkLabel(row, text=m.date[5:16], font=("Segoe UI", 10), text_color="gray").place(relx=1.0, x=-8, y=30, anchor="ne")

    # ------------------------------------------------------------------
    # reader pane
    # ------------------------------------------------------------------
    def _build_reader(self):
        r = self.reader
        self.r_subject = ctk.CTkLabel(r, text="Select a message", font=("Segoe UI", 15, "bold"), anchor="w", wraplength=460, justify="left")
        self.r_subject.pack(fill="x", padx=12, pady=(10, 2))
        meta = ctk.CTkFrame(r, fg_color="transparent")
        meta.pack(fill="x", padx=12)
        self.r_meta = ctk.CTkLabel(meta, text="", anchor="w", justify="left", text_color="gray", font=("Segoe UI", 11))
        self.r_meta.pack(side="left", fill="x", expand=True)
        self.r_level = ctk.CTkLabel(meta, text="", corner_radius=10, width=120, height=22, font=("Segoe UI", 10, "bold"), text_color="white")
        self.r_level.pack(side="right")

        self.r_body = ctk.CTkTextbox(r, wrap="word", font=("Segoe UI", 12))
        self.r_body.pack(fill="both", expand=True, padx=12, pady=8)
        self.r_body.configure(state="disabled")

        self.r_attach = ctk.CTkFrame(r, fg_color="transparent")
        self.r_attach.pack(fill="x", padx=12, pady=(0, 10))

    def open_message(self, uid: str):
        self._set_body("Loading…")
        self.r_subject.configure(text="Loading…")

        def work():
            try:
                msg = self.client.fetch_message(uid)
            except IMAPError as exc:
                self.after(0, lambda: self._set_body(f"Error: {exc}"))
                return
            self.after(0, self._render_message, msg)

        threading.Thread(target=work, daemon=True).start()

    def _render_message(self, msg: EmailMessage):
        self.current = msg
        self.r_subject.configure(text=msg.subject)
        self.r_meta.configure(text=f"From: {msg.sender}\nTo: {msg.to}\nDate: {msg.date}")
        self.r_level.configure(text=LEVEL_NAMES.get(msg.level, f"L{msg.level}"), fg_color=LEVEL_COLORS.get(msg.level, "gray"))

        if msg.is_encrypted:
            text = ("🔒 This message is encrypted with QuMail "
                    f"(Level {msg.level}, key_id={msg.key_id or '?'}).\n"
                    "Decrypt will be available once the crypto module is merged (Day 7+).\n\n"
                    "--- raw envelope ---\n" + msg.body)
        else:
            text = msg.body
        self._set_body(text)

        for w in self.r_attach.winfo_children():
            w.destroy()
        if msg.attachments:
            ctk.CTkLabel(self.r_attach, text=f"Attachments ({len(msg.attachments)})", font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            for att in msg.attachments:
                row = ctk.CTkFrame(self.r_attach, fg_color=("gray90", "gray20"), corner_radius=6)
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=f"📎 {att.filename}  ({att.size_kb} KB · {att.content_type})", anchor="w").pack(side="left", padx=8, fill="x", expand=True)
                ctk.CTkButton(row, text="Download", width=84, command=lambda a=att: self.download(a)).pack(side="right", padx=(4, 6), pady=4)
                ctk.CTkButton(row, text="Preview", width=74, fg_color="gray50", command=lambda a=att: self.preview(a)).pack(side="right", pady=4)

    def _set_body(self, text: str):
        self.r_body.configure(state="normal")
        self.r_body.delete("1.0", "end")
        self.r_body.insert("1.0", text)
        self.r_body.configure(state="disabled")

    # ------------------------------------------------------------------
    # attachments
    # ------------------------------------------------------------------
    def download(self, att: Attachment):
        path = filedialog.asksaveasfilename(title="Save attachment", initialfile=att.filename)
        if not path:
            return
        try:
            with open(path, "wb") as fh:
                fh.write(att.data)
        except OSError as exc:
            messagebox.showerror("QuMail", f"Could not save file:\n{exc}")
            return
        self.status.configure(text=f"Saved {att.filename} → {path}")

    def preview(self, att: Attachment):
        ctype = att.content_type.lower()
        win = ctk.CTkToplevel(self)
        win.title(f"Preview — {att.filename}")
        win.geometry("640x520")
        win.after(100, win.lift)

        if ctype in PREVIEW_IMAGE_TYPES:
            try:
                from PIL import Image  # Pillow ships with customtkinter
                img = Image.open(io.BytesIO(att.data))
                img.thumbnail((600, 460))
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                lbl = ctk.CTkLabel(win, image=photo, text="")
                lbl.image = photo  # keep reference
                lbl.pack(expand=True, padx=10, pady=10)
            except Exception as exc:  # noqa: BLE001 - show any decode error to user
                ctk.CTkLabel(win, text=f"Cannot preview image: {exc}").pack(pady=20)
        elif ctype in PREVIEW_TEXT_TYPES or att.filename.lower().endswith((".txt", ".md", ".csv", ".json", ".py", ".log")):
            box = ctk.CTkTextbox(win, wrap="none", font=("Consolas", 12))
            box.pack(fill="both", expand=True, padx=10, pady=10)
            box.insert("1.0", att.data[:200_000].decode("utf-8", errors="replace"))
            box.configure(state="disabled")
        else:
            ctk.CTkLabel(win, text=f"No preview for {att.content_type}.\nUse Download to save and open it.",
                         justify="center").pack(expand=True)
            ctk.CTkButton(win, text="Download", command=lambda: self.download(att)).pack(pady=(0, 20))
