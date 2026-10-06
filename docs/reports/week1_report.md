# QuMail — Week 1 Report (28 Sep – 04 Oct 2026)

Sprint: SCRUM Sprint 1 · Ticket: SCRUM-28

## Goal of Week 1
Project setup, design (UML), email login + inbox, KM simulator stub, and Level 1 (plain) send/receive working end-to-end.

## What was delivered
| Day | Ticket | Deliverable | Status |
|-----|--------|-------------|--------|
| 1 | SCRUM-9 / 10 / 11 | Repo + structure, vision doc, email-auth research (app passwords, IMAP/SMTP) | Done |
| 2 | SCRUM-12 / 13 | Use case diagram; ADR-001 GUI framework = CustomTkinter; login wireframe | Done |
| 3 | SCRUM-14 / 16 | KM simulator stub (100 x 1 KB keys, CSV key bank); login screen + Gmail IMAP inbox | Done |
| 4 | SCRUM-18 / 19 | Activity diagram compose → encrypt → send → receive → decrypt | Done |
| 5 | SCRUM-21 | Sequence diagram "Send email with quantum key" (Level 2) | Done |
| 6 | SCRUM-24 | Inbox reader pane, attachment preview + download | Done |
| 7 | SCRUM-28 | Compose window, SMTP send, Level 1 wired end-to-end, envelope/level registry | Done |

## Architecture after Week 1
```
src/qumail/
  email/   imap_client.py (login, list, fetch message)   smtp_client.py (send + attachments + X-QuMail headers)
  crypto/  envelope.py (level registry, Level 1, envelope JSON format)
  gui/     app.py  login.py  inbox.py (2-pane + attachments)  compose.py (level dropdown)
  km/      (Week 2 — client for KM simulator API)
SCRUM_Works/SCRUM-14/km_simulator.py   (stub API, to move under src/qumail/km in Week 2)
docs/uml/  wireframe_login_v1, activity_diagram_v1, sequence_send_v1 (+ .md descriptions)
```

## End-to-end test (Level 1)
1. Login with Gmail test account (app password).
2. Compose → To: personal Gmail → Level 1 → Send → "Sent (Level 1)".
3. Mail received in Gmail with header `X-QuMail-Level: 1`.
4. Reply from Gmail → Refresh in QuMail → message opens in reader pane, attachments preview/download OK.

## Gaps / risks carried into Week 2
- Level 2/3 crypto modules and KM client not yet in `develop` — they register via `envelope.register_level()`.
- Team workflow: feature branch → PR to `develop` (no direct pushes to `main`). `main` was merged into `develop` on Day 7.
- `.env`/app passwords never committed; `.gitignore` in place.
- UI polish (list alignment, max width) deferred to Day 13.

## Plan for Week 2 (Days 8–14)
Level 2 (AES-256-GCM with HKDF from quantum key), Level 3 (OTP), KM client, decrypt path in inbox, unit tests, UI polish.
