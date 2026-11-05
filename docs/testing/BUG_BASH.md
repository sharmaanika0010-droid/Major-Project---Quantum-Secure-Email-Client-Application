# Bug bash — end-user session (SCRUM-66)

Setup: Windows 11, `dist\START_QUMAIL.bat` build (QuMail-GUI.exe + QuMail-KM.exe), Gmail account
with app password, second Gmail account as receiver on the same PC. Session goal: use QuMail like a
normal user for one hour (login, read, send at every level, attachments, contacts, audit view,
KM empty, KM offline) and log **everything** that looks wrong, however small.

Severity: **S1** blocks a core flow · **S2** wrong behaviour, workaround exists · **S3** cosmetic / polish.

## Issue log

| ID | Area | Steps | Expected | Actual | Sev | Status |
|---|---|---|---|---|---|---|
| BB-01 | Inbox list | Open inbox with mails from senders of different name length | Sender and subject both start at the left edge of the row | Lines were centred relative to each other (short sender name looked indented); CTkButton centres multi-line text | S3 | **Fixed** — row rebuilt as frame + two left-anchored labels, hover kept (`gui/inbox.py`) |
| BB-02 | Compose | Level 3, leave body empty, no attachment, Send | Nothing to send → warning, no key used | Mail sent, one quantum key reserved for 0 bytes | S2 | **Fixed** — "Nothing to send" check before key request (`gui/compose.py`) |
| BB-03 | Compose / contacts | To: `a@x.com, b@y.com` | Both receive; address book gets 2 contacts | Both received, but address book stored one contact named `a@x.com, b@y.com` | S2 | **Fixed** — `parse_recipients()` splits on `,`/`;`, validates each, remembers each (`gui/ui.py`, `gui/compose.py`) |
| BB-04 | Inbox list | Mail with long subject | Visible "…" when cut | Hard cut at 44 chars, no hint text continues | S3 | **Fixed** — `ellipsize()` helper |
| BB-05 | Compose | Recipient `nobody` (no @) | Clear error | Error shown — OK, but message did not mention comma-separated multiple recipients | S3 | **Fixed** — message updated |
| BB-06 | Send | KM reachable, SMTP password wrong, Level 2 | Clear error, key not wasted | Error shown; key is **burned** (by design – never reuse a key from a failed send) so one key lost per failed attempt | S3 | Accepted — documented in `OTP_KEY_REUSE_REVIEW.md`; login pre-check (SCRUM-63) prevents most cases |
| BB-07 | Receive | Open mail sent under a *different* KM key bank | Message says which KM / key id is missing | "Integrity check failed" / "key not found" — technically right, confusing for a user | S2 | **Fixed** (SCRUM-67) — key fingerprint in envelope → `KeyMismatch` with clear "same Key Manager" message; see `docs/crypto/KEY_FINGERPRINT.md` |
| BB-08 | Packaging | Rebuilt exe after a code change, old `dist` still used | New behaviour | Old behaviour (stale exe) | S3 | Not a bug — `BUILD_EXE.md` now says "re-run build_exe.bat after every change" |
| BB-09 | Receive / AV | Leave inbox idle 10 min with Avast Mail Shield on | Refresh works | IMAP connection dropped; first refresh shows an error, second works | S2 | Known (SCRUM-63 edge-case E11): auto-reconnect on refresh already in place; demo note: disable Mail Shield |
| BB-10 | Send / AV | Level 3 with 2 MB attachment, Avast on | Sent | SMTP upload killed by AV scan | S2 | Known (E12): attachment limit + 180 s timeout; AV off for demo |
| BB-11 | KM simulator | README says port 8000 | Port in README matches server | Server listens on 5000 | S3 | **Fixed** earlier (README corrected) |
| BB-12 | Inbox | Click "Refresh" twice quickly | One refresh | Two background threads, list rendered twice (duplicated rows for a moment) | S3 | **Fixed** — list cleared before render (already in SCRUM-60), re-verified OK |
| BB-13 | Login | Paste app password with spaces `abcd efgh …` | Login works | Works (SCRUM-63) — re-verified | — | Verified |
| BB-14 | Compose | KM empty, choose Level 3 | Offered Level 1 fallback | Fallback button shown — OK | — | Verified |
| BB-15 | Audit view | Open after 20 mails | Newest first, no key material | OK | — | Verified |
| BB-16 | Attachments | Preview `.txt` with Hindi text | Readable | Readable (UTF-8) — OK | — | Verified |

## Summary

| | Count |
|---|---|
| Logged | 16 |
| Fixed in this ticket (PR) | 5 (BB-01…05) |
| Already fixed / verified | 5 (BB-11…16 minus open) |
| Known, documented workaround | 3 (BB-06, BB-09, BB-10) |
| Fixed in SCRUM-67 (crypto/KM) | 1 (BB-07) |

## Tests added
`tests/test_ui_helpers.py`: `test_ellipsize_adds_visible_ellipsis`, `test_parse_recipients_splits_and_validates`.
Full suite: 152 passed, ruff + bandit clean.
