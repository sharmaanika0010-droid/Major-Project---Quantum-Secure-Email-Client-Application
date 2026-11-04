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
