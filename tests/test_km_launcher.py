"""Auto-start of the local Key Manager (desktop-app behaviour)."""
from __future__ import annotations

import sys
from pathlib import Path

from qumail import km_launcher


def test_only_local_urls_are_auto_started():
    assert km_launcher.is_local("http://localhost:5000")
    assert km_launcher.is_local("http://127.0.0.1:5000")
    assert not km_launcher.is_local("http://192.168.1.20:5000")
    assert km_launcher.ensure_running("http://192.168.1.20:5000") is None   # never touches remote KMs


def test_is_up_false_when_nothing_listens():
    assert km_launcher.is_up("http://127.0.0.1:1", timeout=0.3) is False


def test_dev_candidate_points_at_bundled_simulator():
    cmds = km_launcher._candidates()
    assert cmds, "km_simulator.py should be found in development checkout"
    cmd, cwd = cmds[0]
    assert cmd[0] == sys.executable and cmd[1].endswith("km_simulator.py")
    assert (Path(cwd) / "km_simulator.py").exists()


def test_already_running_is_detected(monkeypatch):
    monkeypatch.setattr(km_launcher, "is_up", lambda *_a, **_k: True)
    assert km_launcher.ensure_running("http://localhost:5000") == "already running"
    assert not km_launcher.started_by_us()


def test_stop_without_child_is_safe():
    km_launcher.stop()
    assert not km_launcher.started_by_us()
