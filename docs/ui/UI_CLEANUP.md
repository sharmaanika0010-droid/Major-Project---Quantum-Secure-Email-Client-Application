# UI cleanup pass — Windows (SCRUM-60)

Target: Windows 10/11, 100 %–150 % display scaling, light and dark system theme.

## What changed

| Area | Before | After |
|---|---|---|
| Text rendering | Blurry on 125 %/150 % scaling (Tk not DPI-aware) | Process declared DPI-aware → crisp fonts |
| Message list — sender | `Anika Sharma <sharmaanika0010@gmai…` truncated | Display name only (`Anika Sharma`), address shown in the reader |
| Message list — date | Raw header slice: `6 Oct 2026` vs `02 Nov 2026` misaligned | Parsed and formatted `06 Oct 2026`, local time zone |
| Reader — date | Raw `Mon, 02 Nov 2026 22:04:54 +0530` | `02 Nov 2026 22:04` |
| Dialogs (Compose, Contacts, Audit) | Opened at top-left of the screen | Centred over the main window |
| Keyboard | Only Enter on the login form | **Ctrl+N** new mail, **F5** refresh, **Ctrl+Enter** send, **Esc** closes any dialog, **Ctrl+L** logout |
| Top bar | Six equally weighted buttons | One primary (Compose), secondary buttons grouped, consistent widths |
| Window | 760×620, could shrink until widgets overlapped | Opens 1000×680, min 760×600; dialogs have sensible minimum sizes |
| Fonts/colours | Hard-coded per file | One place: `qumail/gui/ui.py` |
| Login | Focus not set; cursor in no field | Email field focused (or password when email is pre-filled from .env) |

## Checked manually (Windows 11)

- 100 % and 125 % scaling, light and dark theme
- Resize main window to minimum: no overlapping widgets, list and reader both stay usable
- All dialogs open centred; Esc closes; Ctrl+Enter sends from Compose
- Long subjects / senders wrap or truncate without pushing the badge off-screen

Automated: `tests/test_ui_helpers.py` covers the pure helpers (date/sender formatting, DPI call is safe).
