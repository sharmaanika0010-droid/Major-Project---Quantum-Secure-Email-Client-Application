"""Integration fixtures: boots the REAL Key Manager simulator (Flask) on a free port
with a fresh, isolated key bank, and tears it down after the session."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from qumail.km.client import KMClient

REPO = Path(__file__).resolve().parents[2]
SIMULATOR = REPO / "SCRUM_Works" / "SCRUM-14" / "km_simulator.py"

# tiny bootstrap: force Flask to bind the port we chose, then run the simulator as __main__
_BOOT = """
import os, runpy, flask
_orig = flask.Flask.run
def _run(self, *a, **k):
    k.update(host="127.0.0.1", port=int(os.environ["KM_PORT"]), use_reloader=False, debug=False)
    return _orig(self, **k)
flask.Flask.run = _run
runpy.run_path(os.environ["KM_SCRIPT"], run_name="__main__")
"""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def km_server(tmp_path_factory):
    if not SIMULATOR.exists():
        pytest.skip(f"KM simulator not found at {SIMULATOR}")
    work = tmp_path_factory.mktemp("km")
    script = work / "km_simulator.py"
    shutil.copy(SIMULATOR, script)          # keybank.csv is created next to the script -> fresh bank
    port = _free_port()
    env = {**os.environ, "KM_PORT": str(port), "KM_SCRIPT": str(script)}
    proc = subprocess.Popen([sys.executable, "-c", _BOOT], env=env, cwd=work,
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):                     # wait up to ~10 s
        if proc.poll() is not None:
            pytest.fail("KM simulator exited during start-up")
        try:
            if requests.get(f"{url}/keys/status", timeout=0.5).ok:
                break
        except requests.RequestException:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("KM simulator did not come up")
    yield url
    proc.terminate()
    try:
        proc.wait(5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def km(km_server):
    return KMClient(km_server)
