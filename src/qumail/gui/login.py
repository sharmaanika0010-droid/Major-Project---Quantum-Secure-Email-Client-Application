"""Login screen (CustomTkinter) — matches docs/uml/wireframe_login_v1.png."""
from __future__ import annotations

import os
import threading
from typing import Callable

import customtkinter as ctk

from qumail.email.imap_client import IMAPClient, IMAPError, PROVIDERS

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class LoginFrame(ctk.CTkFrame):
    """on_success(client) is called with a connected IMAPClient."""

    def __init__(self, master, on_success: Callable[[IMAPClient], None]):
        super().__init__(master, fg_color="transparent")
        self.on_success = on_success

        ctk.CTkLabel(self, text="Q", width=60, height=60, corner_radius=30,
                     fg_color=("gray85", "gray25"), font=("Segoe UI", 26, "bold")).pack(pady=(30, 10))
        ctk.CTkLabel(self, text="Sign in to QuMail", font=("Segoe UI", 22, "bold")).pack()
        ctk.CTkLabel(self, text="Your mailbox, protected by quantum keys",
                     text_color="gray").pack(pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=40, fill="x")

        ctk.CTkLabel(form, text="Email provider", anchor="w").pack(fill="x")
        self.provider = ctk.CTkOptionMenu(form, values=list(PROVIDERS.keys()), width=380)
        self.provider.pack(fill="x", pady=(2, 12))

        ctk.CTkLabel(form, text="Email address", anchor="w").pack(fill="x")
        self.email = ctk.CTkEntry(form, placeholder_text="you@gmail.com", width=380)
        self.email.pack(fill="x", pady=(2, 12))
        if os.getenv("QUMAIL_EMAIL"):
            self.email.insert(0, os.getenv("QUMAIL_EMAIL"))

        ctk.CTkLabel(form, text="App password", anchor="w").pack(fill="x")
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", pady=(2, 4))
        self.password = ctk.CTkEntry(row, placeholder_text="16-char app password", show="•")
        self.password.pack(side="left", fill="x", expand=True)
        self.show_btn = ctk.CTkButton(row, text="show", width=50, fg_color="transparent",
                                      text_color=("#1f6feb", "#58a6ff"), command=self._toggle_pw)
        self.show_btn.pack(side="left", padx=(6, 0))
        ctk.CTkLabel(form, text="How to create an app password?", text_color=("#1f6feb", "#58a6ff"),
                     font=("Segoe UI", 11), anchor="w").pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(form, text="Key Manager URL", anchor="w").pack(fill="x")
        row2 = ctk.CTkFrame(form, fg_color="transparent")
        row2.pack(fill="x", pady=(2, 12))
        self.km_url = ctk.CTkEntry(row2, placeholder_text="http://localhost:5000")
        self.km_url.insert(0, os.getenv("QUMAIL_KM_URL", "http://localhost:5000"))
        self.km_url.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row2, text="Test", width=70, fg_color="gray70", text_color="black",
                      hover_color="gray60", state="disabled").pack(side="left", padx=(6, 6))
        self.km_status = ctk.CTkLabel(row2, text="● KM not checked", text_color="gray")
        self.km_status.pack(side="left")

        self.remember = ctk.CTkCheckBox(form, text="Remember me on this device")
        self.remember.pack(anchor="w", pady=(0, 12))

        self.sign_in = ctk.CTkButton(form, text="Sign in", height=36, command=self._login)
        self.sign_in.pack(fill="x")

        self.error = ctk.CTkLabel(form, text="", text_color="#e74c3c", wraplength=380)
        self.error.pack(pady=(8, 0))

        self.password.bind("<Return>", lambda _e: self._login())

    # -- helpers ----------------------------------------------------------
    def _toggle_pw(self):
        showing = self.password.cget("show") == ""
        self.password.configure(show="•" if showing else "")
        self.show_btn.configure(text="show" if showing else "hide")

    def _login(self):
        addr = self.email.get().strip()
        pwd = self.password.get().strip()
        prov = self.provider.get()
        if not addr or not pwd:
            self.error.configure(text="Please enter email and app password")
            return
        self.error.configure(text="")
        self.sign_in.configure(state="disabled", text="Signing in…")

        def work():
            client = IMAPClient(prov, addr, pwd)
            try:
                client.connect()
            except IMAPError as exc:
                self.after(0, self._fail, str(exc))
                return
            self.after(0, self._ok, client)

        threading.Thread(target=work, daemon=True).start()  # keep UI responsive

    def _fail(self, message: str):
        self.sign_in.configure(state="normal", text="Sign in")
        self.error.configure(text=message)

    def _ok(self, client: IMAPClient):
        self.sign_in.configure(state="normal", text="Sign in")
        self.on_success(client)
