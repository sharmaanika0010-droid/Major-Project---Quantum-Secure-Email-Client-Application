"""Address book (SCRUM-57).

Stores recipients together with the information QuMail needs for key exchange:

* preferred security level for that person (1–4),
* the recipient's Key-Manager peer id (the SAE id in a real QKD network),
* free-text notes (e.g. "shares KM 'lab-km-1' with us").

Data lives in a small JSON file *outside* the repository
(default ``~/.qumail/contacts.json``; override with ``QUMAIL_CONTACTS_FILE``).
No passwords or key material are ever written here.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LEVELS = (1, 2, 3, 4)


class ContactError(ValueError):
    """Invalid contact data (bad e-mail, unknown level …)."""


@dataclass
class Contact:
    email: str
    name: str = ""
    preferred_level: int = 2
    km_peer_id: str = ""
    notes: str = ""
    last_used: float = 0.0          # unix time of the last mail sent to this contact
    mails_sent: int = 0

    def __post_init__(self):
        self.email = self.email.strip().lower()
        if not _EMAIL_RE.match(self.email):
            raise ContactError(f"'{self.email}' is not a valid e-mail address")
        self.preferred_level = int(self.preferred_level)
        if self.preferred_level not in LEVELS:
            raise ContactError(f"preferred level must be one of {LEVELS}")
        self.name = self.name.strip()
        self.km_peer_id = self.km_peer_id.strip()

    @property
    def display(self) -> str:
        return f"{self.name} <{self.email}>" if self.name else self.email


@dataclass
class ContactBook:
    path: Path
    _items: Dict[str, Contact] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self.path = Path(self.path).expanduser()
        self.load()

    # -- persistence --------------------------------------------------------
    def load(self) -> None:
        self._items = {}
        if not self.path.is_file():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        except (OSError, ValueError):
            return                                  # corrupt file → start empty, never crash the GUI
        for entry in raw if isinstance(raw, list) else []:
            try:
                c = Contact(**{k: v for k, v in entry.items() if k in Contact.__dataclass_fields__})
            except (TypeError, ContactError):
                continue
            self._items[c.email] = c

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(c) for c in self.all()]
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)                      # atomic on Windows and POSIX

    # -- CRUD ---------------------------------------------------------------
    def all(self) -> List[Contact]:
        return sorted(self._items.values(), key=lambda c: (c.name or c.email).lower())

    def get(self, email: str) -> Optional[Contact]:
        return self._items.get((email or "").strip().lower())

    def upsert(self, contact: Contact) -> Contact:
        old = self._items.get(contact.email)
        if old:                                     # keep usage statistics across edits
            contact.last_used = old.last_used
            contact.mails_sent = old.mails_sent
        self._items[contact.email] = contact
        self.save()
        return contact

    def remove(self, email: str) -> bool:
        gone = self._items.pop((email or "").strip().lower(), None) is not None
        if gone:
            self.save()
        return gone

    def search(self, text: str) -> List[Contact]:
        q = (text or "").strip().lower()
        if not q:
            return self.all()
        return [c for c in self.all() if q in c.email or q in c.name.lower()]

    # -- used by Compose ----------------------------------------------------
    def remember(self, email: str, level: int) -> Contact:
        """Called after a successful send: creates the contact if unknown and
        records the level actually used, so next time it is pre-selected."""
        c = self.get(email) or Contact(email=email, preferred_level=level if level in LEVELS else 1)
        c.preferred_level = level if level in LEVELS else c.preferred_level
        c.last_used = time.time()
        c.mails_sent += 1
        self._items[c.email] = c
        self.save()
        return c

    def __len__(self) -> int:
        return len(self._items)


_book: Optional[ContactBook] = None


def get_book() -> ContactBook:
    """Process-wide address book at the configured path."""
    global _book
    if _book is None:
        from qumail.config import get_settings
        _book = ContactBook(Path(get_settings().contacts_file))
    return _book
