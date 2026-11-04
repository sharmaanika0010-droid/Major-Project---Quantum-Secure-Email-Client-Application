"""SCRUM-57: address book with key-exchange info."""
from __future__ import annotations

import json

import pytest

from qumail.contacts import Contact, ContactBook, ContactError


@pytest.fixture
def book(tmp_path):
    return ContactBook(tmp_path / "contacts.json")


def test_add_get_and_persist(book, tmp_path):
    book.upsert(Contact(email="Amit@Example.com", name="Amit", preferred_level=3, km_peer_id="SAE-amit"))
    assert book.get("amit@example.com").name == "Amit"          # e-mail normalised to lower case
    reopened = ContactBook(tmp_path / "contacts.json")
    c = reopened.get("amit@example.com")
    assert (c.preferred_level, c.km_peer_id) == (3, "SAE-amit")


def test_invalid_email_and_level_rejected():
    with pytest.raises(ContactError):
        Contact(email="not-an-email")
    with pytest.raises(ContactError):
        Contact(email="a@b.co", preferred_level=9)


def test_remove_and_search(book):
    book.upsert(Contact(email="umang@example.com", name="Umang Goswami"))
    book.upsert(Contact(email="anika@example.com", name="Anika"))
    assert [c.name for c in book.search("uma")] == ["Umang Goswami"]
    assert [c.name for c in book.search("example")] == ["Anika", "Umang Goswami"]   # sorted by name
    assert book.remove("umang@example.com") is True
    assert book.remove("umang@example.com") is False
    assert len(book) == 1


def test_remember_after_send_creates_and_updates(book):
    c = book.remember("new@example.com", level=4)
    assert (c.preferred_level, c.mails_sent) == (4, 1)
    c = book.remember("new@example.com", level=2)
    assert (c.preferred_level, c.mails_sent) == (2, 2)
    assert c.last_used > 0


def test_upsert_keeps_usage_stats(book):
    book.remember("x@example.com", level=2)
    book.upsert(Contact(email="x@example.com", name="X", preferred_level=3))
    assert book.get("x@example.com").mails_sent == 1


def test_corrupt_file_does_not_crash(tmp_path):
    p = tmp_path / "contacts.json"
    p.write_text("{not json")
    assert len(ContactBook(p)) == 0


def test_file_contains_no_secrets(book, tmp_path):
    book.upsert(Contact(email="a@example.com", name="A", notes="shares lab KM"))
    data = json.loads((tmp_path / "contacts.json").read_text())
    assert set(data[0]) == {"email", "name", "preferred_level", "km_peer_id", "notes", "last_used", "mails_sent"}


def test_default_location_is_outside_repo(monkeypatch, tmp_path):
    from qumail import config, contacts
    monkeypatch.delenv("QUMAIL_CONTACTS_FILE", raising=False)
    s = config.Settings.from_env(dotenv=False)
    assert s.contacts_file.startswith("~")
    monkeypatch.setenv("QUMAIL_CONTACTS_FILE", str(tmp_path / "c.json"))
    config.reload(dotenv=False)
    contacts._book = None
    assert contacts.get_book().path == tmp_path / "c.json"
    contacts._book = None
    config.reload(dotenv=False)
