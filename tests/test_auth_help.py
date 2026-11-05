"""SCRUM-63: Gmail/Yahoo login edge cases — 2FA, app passwords, wrong provider, network."""
import pytest

from qumail.email import auth_help as ah
from qumail.email.imap_client import IMAPClient
from qumail.email.smtp_client import SMTPClient


def test_app_password_spaces_are_removed():
    assert ah.normalize_app_password("abcd efgh ijkl mnop") == "abcdefghijklmnop"
    assert ah.looks_like_app_password("abcd efgh ijkl mnop")
    assert not ah.looks_like_app_password("MyRealPassw0rd!")
    assert IMAPClient("Gmail", " a@gmail.com ", "abcd efgh ijkl mnop")._password == "abcdefghijklmnop"
    assert SMTPClient("Yahoo", "a@yahoo.com", "abcd efgh ijkl mnop")._password == "abcdefghijklmnop"


@pytest.mark.parametrize("addr,prov", [
    ("x@gmail.com", "Gmail"), ("X@GoogleMail.com", "Gmail"),
    ("y@yahoo.com", "Yahoo"), ("y@yahoo.co.in", "Yahoo"), ("y@ymail.com", "Yahoo"),
    ("z@outlook.com", None), ("not-an-email", None),
])
def test_provider_detection(addr, prov):
    assert ah.provider_for_address(addr) == prov


def test_precheck_catches_input_mistakes():
    assert ah.precheck("Gmail", "anika", "x" * 16).kind == "input"
    a = ah.precheck("Yahoo", "a@gmail.com", "abcdabcdabcdabcd")
    assert a.kind == "input" and "Gmail" in a.message            # wrong provider for the address
    assert ah.precheck("Gmail", "a@gmail.com", "").kind == "input"
    assert "normal account password" in ah.precheck("Gmail", "a@gmail.com", "Pass@123").message
    assert ah.precheck("Gmail", "a@gmail.com", "abcd efgh ijkl mnop") is None


def test_gmail_2fa_on_normal_password():
    a = ah.explain_login_error("Gmail", "Login failed: [ALERT] Application-specific password required", "MyPass!1")
    assert "app password" in a.message and a.help_url == ah.HELP_URLS["Gmail"]


def test_gmail_2fa_off_normal_password():
    a = ah.explain_login_error("Gmail", "Login failed: [AUTHENTICATIONFAILED] Invalid credentials (Failure)", "MyPass!1")
    assert "2-step verification" in a.message and "app password" in a.message


def test_wrong_or_revoked_app_password():
    a = ah.explain_login_error("Yahoo", "Login failed: [AUTHENTICATIONFAILED] LOGIN failed", "abcdabcdabcdabcd")
    assert "rejected the app password" in a.message and a.help_url == ah.HELP_URLS["Yahoo"]


def test_smtp_535_maps_like_imap():
    a = ah.explain_login_error("Gmail", "SMTP login failed: 535-5.7.8 Username and Password not accepted", "abcdabcdabcdabcd")
    assert a.kind == "auth" and "app password" in a.message


def test_network_errors():
    assert ah.explain_login_error("Gmail", "Cannot reach imap.gmail.com: [Errno 11001] getaddrinfo failed").kind == "network"
    assert "timed out" in ah.explain_login_error("Gmail", "Cannot reach imap.gmail.com: timed out").message
    assert "Mail Shield" in ah.explain_login_error("Yahoo", "Cannot reach x: [SSL: CERTIFICATE_VERIFY_FAILED]").message


def test_web_login_required_and_lockout():
    assert "browser" in ah.explain_login_error("Gmail", "[ALERT] Web login required: https://support.google.com").message
    assert "locked" in ah.explain_login_error("Gmail", "[ALERT] Too many simultaneous connections").message


def test_unknown_error_falls_through_unchanged():
    assert ah.explain_login_error("Gmail", "something odd").message == "something odd"
