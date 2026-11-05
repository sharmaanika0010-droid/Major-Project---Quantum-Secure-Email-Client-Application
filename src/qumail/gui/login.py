"""Login screen (CustomTkinter) — matches docs/uml/wireframe_login_v1.png."""
from __future__ import annotations

import threading
import webbrowser
from typing import Callable

import customtkinter as ctk

from qumail import audit
from qumail.config import get_settings
from qumail.email import auth_help
from qumail.email.imap_client import PROVIDERS, IMAPClient, IMAPError
from qumail.email.smtp_client import SMTPClient
from qumail.km.client import KMClient, KMError

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class LoginFrame(ctk.CTkFrame):
    """on_success(imap, smtp) is called with a connected IMAPClient and a ready SMTPClient."""

    def __init__(self, master, on_success: Callable[[IMAPClient], None]):
        super().__init__(master, fg_color="transparent")
        self.on_success = on_success
        cfg = get_settings()

        ctk.CTkLabel(self, text="Q", width=60, height=60, corner_radius=30,
                     fg_color=("gray85", "gray25"), font=("Segoe UI", 26, "bold")).pack(pady=(30, 10))
        ctk.CTkLabel(self, text="Sign in to QuMail", font=("Segoe UI", 22, "bold")).pack()
        ctk.CTkLabel(self, text="Your mailbox, protected by quantum keys",
                     text_color="gray").pack(pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=40, fill="x")

        ctk.CTkLabel(form, text="Email provider", anchor="w").pack(fill="x")
        self.provider = ctk.CTkOptionMenu(form, values=list(PROVIDERS.keys()), width=380)
        self.provider.set(cfg.provider)
        self.provider.pack(fill="x", pady=(2, 12))

        ctk.CTkLabel(form, text="Email address", anchor="w").pack(fill="x")
        self.email = ctk.CTkEntry(form, placeholder_text="you@gmail.com", width=380)
        self.email.pack(fill="x", pady=(2, 12))
        if cfg.email:
            self.email.insert(0, cfg.email)

        ctk.CTkLabel(form, text="App password", anchor="w").pack(fill="x")
        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", pady=(2, 4))
        self.password = ctk.CTkEntry(row, placeholder_text="16-char app password", show="•")
        self.password.pack(side="left", fill="x", expand=True)
        self.show_btn = ctk.CTkButton(row, text="show", width=50, fg_color="transparent",
                                      text_color=("#1f6feb", "#58a6ff"), command=self._toggle_pw)
        self.show_btn.pack(side="left", padx=(6, 0))
        self.help_lbl = ctk.CTkLabel(form, text="How to create an app password?", text_color=("#1f6feb", "#58a6ff"),
                                     font=("Segoe UI", 11, "underline"), anchor="w", cursor="hand2")
        self.help_lbl.pack(fill="x", pady=(0, 12))
        self.help_lbl.bind("<Button-1>", lambda _e: self._open_help())
        self._help_url = None
        # SCRUM-63: typing a gmail/yahoo address selects the matching provider automatically
        self.email.bind("<FocusOut>", lambda _e: self._sync_provider())

        ctk.CTkLabel(form, text="Key Manager URL", anchor="w").pack(fill="x")
        row2 = ctk.CTkFrame(form, fg_color="transparent")
        row2.pack(fill="x", pady=(2, 12))
        self.km_url = ctk.CTkEntry(row2, placeholder_text=cfg.km_url)
        self.km_url.insert(0, cfg.km_url)
        self.km_url.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row2, text="Test", width=70, command=self._test_km).pack(side="left", padx=(6, 6))
        self.km_status = ctk.CTkLabel(row2, text="● KM not checked", text_color="gray")
        self.km_status.pack(side="left")

        self.remember = ctk.CTkCheckBox(form, text="Remember me on this device")
        self.remember.pack(anchor="w", pady=(0, 12))

        self.sign_in = ctk.CTkButton(form, text="Sign in", height=36, command=self._login)
        self.sign_in.pack(fill="x")

        self.error = ctk.CTkLabel(form, text="", text_color="#e74c3c", wraplength=380)
        self.error.pack(pady=(8, 0))

        self.password.bind("<Return>", lambda _e: self._login())
        self.email.bind("<Return>", lambda _e: self.password.focus_set())
        # SCRUM-60: focus the first empty field
        self.after(200, lambda: (self.password if cfg.email else self.email).focus_set())

    # -- helpers ----------------------------------------------------------
    def _test_km(self):
        self.km_status.configure(text="● checking…", text_color="gray")
        url = self.km_url.get().strip()

        def work():
            try:
                st = KMClient(url, timeout=get_settings().km_timeout).status()
                txt, col = f"● KM OK — {st.get('available', '?')} keys available", "#2ecc71"
            except KMError as exc:
                txt, col = f"● {exc}", "#e74c3c"
            self.after(0, lambda: self.km_status.configure(text=txt[:60], text_color=col))

        threading.Thread(target=work, daemon=True).start()

    def _toggle_pw(self):
        showing = self.password.cget("show") == ""
        self.password.configure(show="•" if showing else "")
        self.show_btn.configure(text="show" if showing else "hide")

    def _open_help(self):
        webbrowser.open(self._help_url or auth_help.HELP_URLS.get(self.provider.get(), auth_help.HELP_URLS["Gmail"]))

    def _sync_provider(self):
        guessed = auth_help.provider_for_address(self.email.get())
        if guessed and guessed in PROVIDERS:
            self.provider.set(guessed)

    def _login(self):
        addr = self.email.get().strip()
        pwd = auth_help.normalize_app_password(self.password.get())
        prov = self.provider.get()
        advice = auth_help.precheck(prov, addr, pwd)
        if advice:
            self._help_url = advice.help_url
            guessed = auth_help.provider_for_address(addr)
            if guessed and guessed != prov and guessed in PROVIDERS:
                self.provider.set(guessed)             # fix it for them and let them press Sign in again
            self.error.configure(text=advice.message)
            return
        self.error.configure(text="")
        self.sign_in.configure(state="disabled", text="Signing in…")

        def work():
            client = IMAPClient(prov, addr, pwd)
            try:
                client.connect()
            except IMAPError as exc:
                advice = auth_help.explain_login_error(prov, str(exc), pwd)
                self._help_url = advice.help_url
                self.after(0, self._fail, advice.message)
                return
            cfg = get_settings()
            self.after(0, self._ok, client, SMTPClient(prov, addr, pwd),
                       KMClient(self.km_url.get().strip(), timeout=cfg.km_timeout))

        threading.Thread(target=work, daemon=True).start()  # keep UI responsive

    def _fail(self, message: str):
        self.sign_in.configure(state="normal", text="Sign in")
        self.error.configure(text=message)

    def _ok(self, client: IMAPClient, smtp: SMTPClient, km: KMClient):
        audit.log("login", address=client.address, provider=self.provider.get(), km_url=km.base_url)
        self.sign_in.configure(state="normal", text="Sign in")
        self.on_success(client, smtp, km)
