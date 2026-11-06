"""Auto-start the local Key Manager so QuMail behaves like a normal desktop app (no console needed).

When the configured KM URL points at this machine and nothing answers there, we start the
simulator ourselves — `QuMail-KM.exe` next to the client in the packaged build, or
`src/km_simulator/km_simulator.py` with the current interpreter in development — hidden
(no console window), logging to ~/.qumail/km.log. The child is stopped again when the app exits.
If the URL is remote (a shared KM on the LAN) nothing is started.
"""
from __future__ import annotations

import atexit
import contextlib
import subprocess  # nosec B404 - we only ever launch our own bundled Key Manager binary
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

_child: subprocess.Popen | None = None
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def is_local(km_url: str) -> bool:
    return (urlparse(km_url).hostname or "") in LOCAL_HOSTS


def is_up(km_url: str, timeout: float = 1.0) -> bool:
    try:
        return requests.get(f"{km_url.rstrip('/')}/keys/status", timeout=timeout).status_code == 200
    except requests.RequestException:
        return False


def _candidates() -> list[tuple[list[str], Path]]:
    """(command, working directory) options, most specific first."""
    out: list[tuple[list[str], Path]] = []
    if getattr(sys, "frozen", False):                              # packaged: dist\QuMail\QuMail.exe
        here = Path(sys.executable).resolve().parent
        for exe in (here.parent / "QuMail-KM" / "QuMail-KM.exe", here / "QuMail-KM" / "QuMail-KM.exe",
                    here / "QuMail-KM.exe"):
            if exe.exists():
                out.append(([str(exe)], exe.parent))
    else:                                                          # development: python -m qumail.gui.app
        script = Path(__file__).resolve().parents[1] / "km_simulator" / "km_simulator.py"
        if script.exists():
            out.append(([sys.executable, str(script)], script.parent))
    return out


def ensure_running(km_url: str, wait_s: float = 12.0) -> str | None:
    """Return a short status note ('started', 'already running', None if not local / not possible)."""
    if not is_local(km_url):
        return None
    if is_up(km_url):
        return "already running"
    for cmd, cwd in _candidates():
        if _start(cmd, cwd):
            deadline = time.time() + wait_s
            while time.time() < deadline:
                if is_up(km_url, timeout=0.5):
                    return "started"
                time.sleep(0.4)
            return "starting"                                       # slow machine — GUI will retry on Test/Refresh
    return None


def _start(cmd: list[str], cwd: Path) -> bool:
    global _child
    log_dir = Path.home() / ".qumail"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = open(log_dir / "km.log", "ab")                             # noqa: SIM115 - kept open for the child's lifetime
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        _child = subprocess.Popen(cmd, cwd=str(cwd), stdout=log, stderr=subprocess.STDOUT,  # nosec B603
                                  stdin=subprocess.DEVNULL, creationflags=flags)
    except OSError:
        log.close()
        return False
    atexit.register(stop)
    return True


def stop() -> None:
    """Terminate the KM we started (never one the user started themselves)."""
    global _child
    if _child is None:
        return
    with contextlib.suppress(OSError):
        _child.terminate()
        try:
            _child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _child.kill()
    _child = None


def started_by_us() -> bool:
    return _child is not None
