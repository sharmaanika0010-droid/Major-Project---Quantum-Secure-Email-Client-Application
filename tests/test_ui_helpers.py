"""SCRUM-60: pure helpers behind the UI cleanup (no Tk needed)."""
from qumail.gui import ui


def test_friendly_date_formats_rfc2822():
    out = ui.friendly_date("Mon, 02 Nov 2026 22:04:54 +0530")
    assert out.endswith(("22:04", ":34", ":04")) and "Nov 2026" in out      # local-tz conversion may shift hours
    assert ui.friendly_date("Mon, 02 Nov 2026 22:04:54 +0530", with_time=False).startswith("0")  # zero-padded day


def test_friendly_date_is_robust():
    assert ui.friendly_date("") == ""
    assert ui.friendly_date("garbage date") == "garbage date"


def test_friendly_sender():
    assert ui.friendly_sender("Anika Sharma <sharmaanika0010@gmail.com>") == "Anika Sharma"
    assert ui.friendly_sender('"Amit, C" <amit@example.com>') == "Amit, C"
    assert ui.friendly_sender("<qumailtest71@gmail.com>") == "qumailtest71@gmail.com"
    assert ui.friendly_sender("qumailtest71@gmail.com") == "qumailtest71@gmail.com"
    assert ui.friendly_sender("") == ""


def test_dpi_helper_is_noop_off_windows():
    ui.enable_windows_dpi()        # must never raise, on any OS


# ---- bug bash (SCRUM-66) ---------------------------------------------------
from qumail.gui.ui import ellipsize, parse_recipients  # noqa: E402


def test_ellipsize_adds_visible_ellipsis():
    assert ellipsize("short", 10) == "short"
    assert ellipsize("a" * 50, 10).endswith("…") and len(ellipsize("a" * 50, 10)) == 10
    assert ellipsize("", 5) == ""


def test_parse_recipients_splits_and_validates():
    assert parse_recipients("a@x.com") == ["a@x.com"]
    assert parse_recipients(" a@x.com , b@y.com;a@x.com ") == ["a@x.com", "b@y.com"]
    for bad in ("", "nobody", "a@", "@x.com", "a@x.com, nobody", "a b@x.com"):
        assert parse_recipients(bad) == [], bad
