"""SCRUM-56: configuration comes from the environment / .env, never from code literals."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from qumail import config

ROOT = Path(__file__).resolve().parents[1]
QUMAIL_VARS = [
    "QUMAIL_EMAIL", "QUMAIL_PROVIDER", "QUMAIL_KM_URL", "QUMAIL_KM_TIMEOUT",
    "QUMAIL_SMTP_PORT", "QUMAIL_SMTP_TIMEOUT", "QUMAIL_IMAP_TIMEOUT",
    "QUMAIL_MAX_FILES", "QUMAIL_MAX_FILE_MB", "QUMAIL_MAX_TOTAL_MB", "QUMAIL_LEVEL3_WARN_KB",
    "QUMAIL_CONTACTS_FILE",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for v in QUMAIL_VARS:
        monkeypatch.delenv(v, raising=False)
    yield
    config.reload(dotenv=False)


def test_defaults_without_env():
    s = config.Settings.from_env(dotenv=False)
    assert s.km_url == "http://localhost:5000"
    assert s.provider == "Gmail"
    assert s.email == ""
    assert (s.smtp_timeout, s.km_timeout, s.max_files) == (30, 5.0, 10)


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("QUMAIL_EMAIL", "anika@example.com")
    monkeypatch.setenv("QUMAIL_PROVIDER", "yahoo")
    monkeypatch.setenv("QUMAIL_KM_URL", "http://10.0.0.5:5000/")
    monkeypatch.setenv("QUMAIL_SMTP_TIMEOUT", "180")
    s = config.Settings.from_env(dotenv=False)
    assert s.email == "anika@example.com"
    assert s.provider == "Yahoo"
    assert s.km_url == "http://10.0.0.5:5000"      # trailing slash stripped
    assert s.smtp_timeout == 180


@pytest.mark.parametrize("name,value", [
    ("QUMAIL_SMTP_TIMEOUT", "abc"),
    ("QUMAIL_SMTP_TIMEOUT", "-5"),
    ("QUMAIL_MAX_FILES", "999"),
    ("QUMAIL_KM_URL", "localhost:5000"),           # missing scheme
    ("QUMAIL_PROVIDER", "Outlook"),
])
def test_bad_values_fall_back_to_defaults(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    s = config.Settings.from_env(dotenv=False)
    d = config.Settings()
    assert s.smtp_timeout == d.smtp_timeout
    assert s.max_files == d.max_files
    assert s.km_url == d.km_url
    assert s.provider == d.provider


def test_dotenv_file_is_read(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("QUMAIL_KM_URL=http://km.local:5000\nQUMAIL_MAX_FILES=3\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "_ROOT", tmp_path)
    s = config.Settings.from_env()
    assert s.km_url == "http://km.local:5000"
    assert s.max_files == 3
    assert s.env_file.endswith(".env")


def test_password_is_never_a_setting():
    names = {f.name.lower() for f in config.fields(config.Settings)}
    assert not any("pass" in n or "secret" in n or "token" in n for n in names)


def test_env_example_lists_every_variable():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    missing = [v for v in QUMAIL_VARS if v not in text]
    assert not missing, f".env.example is missing: {missing}"


# --- repository hygiene -------------------------------------------------------

FORBIDDEN_TRACKED = (".env", "credentials.json", "token.json", "keybank.csv")
APP_PASSWORD = re.compile(r"\b[a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4}\b")   # Gmail app-password shape


def _tracked_files() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return out.splitlines()


def test_no_secret_files_are_tracked():
    bad = [f for f in _tracked_files() if Path(f).name in FORBIDDEN_TRACKED]
    assert not bad, f"secret files committed to git: {bad}"


def test_no_hardcoded_app_passwords_in_source():
    hits = []
    for py in (ROOT / "src" / "qumail").rglob("*.py"):
        for i, line in enumerate(py.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if APP_PASSWORD.search(line):
                hits.append(f"{py.relative_to(ROOT)}:{i}")
    assert not hits, f"possible app passwords in code: {hits}"


def test_source_has_no_hardcoded_km_url_outside_config():
    hits = []
    for py in (ROOT / "src" / "qumail").rglob("*.py"):
        if py.name == "config.py":
            continue
        if "localhost:5000" in py.read_text(encoding="utf-8", errors="ignore"):
            hits.append(str(py.relative_to(ROOT)))
    assert not hits, f"KM URL hardcoded outside config.py: {hits}"
