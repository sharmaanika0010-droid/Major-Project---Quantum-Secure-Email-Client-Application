\# ADR-001: GUI Framework Selection — QuMail



Date: 29 Sep 2026 | Author: Anika Sharma | Ticket: SCRUM-13 | Status: Accepted



\## Context

QuMail needs a Windows desktop GUI with login, inbox, compose (with attachments),

a security-level selector (1/2/3/4) and a key-status indicator. The team stack is Python.

The app must package into a single .exe with PyInstaller.



\## Options considered



| Criteria                     | CustomTkinter          | PyQt6 / PySide6       | Kivy            | Electron + Python |

|------------------------------|------------------------|-----------------------|-----------------|-------------------|

| Learning curve               | Very low (built-in)    | Medium                | Medium-high     | High (2 languages)|

| Windows look \& feel          | Good (modern themes)   | Excellent (native)    | Touch-oriented  | Good              |

| Widgets needed               | Sufficient             | Excellent             | Limited         | Good              |

| PyInstaller build size       | \~15 MB                 | \~60 MB                | \~40 MB          | 150+ MB           |

| Licence                      | PSF                    | LGPL / GPL            | MIT             | MIT               |



\## Decision

CustomTkinter. Zero extra learning for the team, ships with Python, modern dark/light

theme out of the box, smallest executable, and enough widgets for all planned screens.

Fallback: ttk.Treeview for the inbox table if needed — no framework change required.



\## Consequences

\- customtkinter added to requirements.txt

\- GUI code lives in src/qumail/gui/, one file per screen (login.py, inbox.py, compose.py)

\- GUI talks to crypto/email modules only through a controller layer (keeps UI testable

&#x20; and matches the Component Diagram)

