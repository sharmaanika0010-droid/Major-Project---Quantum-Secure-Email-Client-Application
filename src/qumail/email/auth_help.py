"""Gmail / Yahoo login edge cases (SCRUM-63).

Both providers reject the normal account password for IMAP/SMTP and require a
16-character *app password* that only exists once 2-step verification is on.
Users hit the same handful of problems; this module turns the cryptic server
replies into one clear sentence plus the right help link, and fixes the input
mistakes we can fix silently (spaces in the app password, wrong provider for
the address).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

HELP_URLS = {
    "Gmail": "https://myaccount.google.com/apppasswords",
    "Yahoo": "https://login.yahoo.com/account/security",
}
TWO_FA_URLS = {
    "Gmail": "https://myaccount.google.com/signinoptions/two-step-verification",
    "Yahoo": "https://login.yahoo.com/account/security",
}

_DOMAIN_PROVIDER = {
    "gmail.com": "Gmail", "googlemail.com": "Gmail",
    "yahoo.com": "Yahoo", "yahoo.co.in": "Yahoo", "yahoo.in": "Yahoo", "yahoo.co.uk": "Yahoo",
    "ymail.com": "Yahoo", "rocketmail.com": "Yahoo",
}
_EMAIL_RE = re.compile(r"^[^@\s]+@([^@\s]+\.[^@\s]+)$")


def provider_for_address(address: str) -> Optional[str]:
    """'x@gmail.com' → 'Gmail'; unknown domain → None (user's choice stands)."""
    m = _EMAIL_RE.match((address or "").strip().lower())
    return _DOMAIN_PROVIDER.get(m.group(1)) if m else None


def normalize_app_password(raw: str) -> str:
    """Google shows app passwords as four groups of four letters; users paste the spaces too."""
    return re.sub(r"\s+", "", raw or "")


def looks_like_app_password(pwd: str) -> bool:
    p = normalize_app_password(pwd)
    return len(p) == 16 and p.isalnum()


@dataclass
class LoginAdvice:
    message: str                   # one sentence for the red label
    help_url: Optional[str] = None  # opened by the "How to create an app password?" link
    kind: str = "auth"             # auth | network | input


def explain_login_error(provider: str, raw_error: str, typed: str = "") -> LoginAdvice:
    """Map an IMAP/SMTP failure (and what the user typed) to actionable advice."""
    err = (raw_error or "").lower()
    help_url = HELP_URLS.get(provider)
    pwd = normalize_app_password(typed)

    # --- network ---------------------------------------------------------
    if any(s in err for s in ("getaddrinfo", "name or service not known", "nodename nor servname",
                              "11001", "temporary failure in name resolution")):
        return LoginAdvice("No internet connection (cannot resolve the mail server). Check Wi-Fi/VPN and retry.", None, "network")
    if any(s in err for s in ("timed out", "timeout", "10060")):
        return LoginAdvice("Connection to the mail server timed out — a firewall or antivirus mail shield may be blocking port 993/465.", None, "network")
    if "certificate" in err or "ssl" in err:
        return LoginAdvice("Secure connection failed (TLS certificate). Antivirus mail scanning often causes this — disable Mail Shield and retry.", None, "network")

    # --- provider specific authentication replies --------------------------
    if "application-specific password required" in err or "application specific password" in err:
        return LoginAdvice("2-step verification is ON, so Gmail needs an app password — not your normal password.", help_url)
    if "web login required" in err or "webalert" in err:
        return LoginAdvice("Gmail blocked the sign-in. Open Gmail in a browser once, approve the security alert, then retry.", help_url)
    if "lockdown" in err or "too many" in err or "rate" in err:
        return LoginAdvice("Too many failed attempts — the account is temporarily locked. Wait 10–15 minutes.", help_url)
    if "authenticationfailed" in err or "invalid credentials" in err or "login failed" in err \
            or "authentication failed" in err or "535" in err or "bad credentials" in err:
        if pwd and not looks_like_app_password(pwd):
            return LoginAdvice(
                f"{provider} does not accept the account password here. Turn on 2-step verification, "
                f"create a 16-character app password and paste it instead.", help_url)
        return LoginAdvice(
            f"{provider} rejected the app password. Generate a new one (old ones stop working when 2-step "
            f"verification is changed or the password is reset) and make sure the e-mail address is right.", help_url)
    if "imap" in err and ("disabled" in err or "not enabled" in err):
        return LoginAdvice("IMAP access is disabled for this account — enable it in the mailbox settings (Gmail: Settings → Forwarding and POP/IMAP).", help_url)

    # --- fallback ----------------------------------------------------------
    return LoginAdvice(raw_error or "Login failed — check e-mail / app password.", help_url)


def precheck(provider: str, address: str, typed: str) -> Optional[LoginAdvice]:
    """Catch input mistakes before touching the network. Returns advice or None if fine."""
    if not _EMAIL_RE.match((address or "").strip()):
        return LoginAdvice("Enter a full e-mail address, e.g. name@gmail.com", None, "input")
    guessed = provider_for_address(address)
    if guessed and guessed != provider:
        return LoginAdvice(f"'{address.strip()}' is a {guessed} address but '{provider}' is selected — switched to {guessed}.",
                           None, "input")
    pwd = normalize_app_password(typed)
    if not pwd:
        return LoginAdvice("Enter the 16-character app password (not your normal password).", HELP_URLS.get(provider), "input")
    if len(pwd) < 16 and not pwd.isalnum():
        return LoginAdvice("That looks like a normal account password. Gmail/Yahoo need an app password (16 letters).",
                           HELP_URLS.get(provider), "input")
    return None
