# QuMail — Week 2 Report (5 – 11 Oct 2026)

Project: QuMail — Quantum Secure Email Client · Sprint 2–3 · Report date: 11 Oct 2026

## 1. Summary
Week 2 goal was "encrypted mail end-to-end". Achieved: Level 2 (AES-256-GCM with quantum key) and Level 3 (One-Time Pad) work over a real Gmail account with attachments, the client handles key-bank depletion and KM outages gracefully, and a CI pipeline with unit + integration tests and a coverage report is live.

## 2. Completed this week
| Day | Ticket | Deliverable | Status |
|---|---|---|---|
| 6 | SCRUM-28 | Attachment send/receive + preview | Done |
| 7 | SCRUM-29 | Branch sync, KM client groundwork | Done |
| 8 | SCRUM-33 | Level 2: HKDF → AES-256-GCM, `.qenc` attachments, IMAP auto-reconnect | Done |
| 9 | SCRUM-34 | Level 3: OTP + HMAC, key-length vs message-length check, crypto pipeline module | Done |
| 10 | SCRUM-39 | Key-bank depletion: key indicator, EMPTY/offline states, Level 1 fallback, burn key on failed send | Done |
| 11 | SCRUM-40 | GitHub Actions CI (ruff + 34 unit tests, Py 3.11/3.13), test plan, branch protection | Done |
| 12 | SCRUM-45 | Integration test: full Level 3 flow with attachment vs real KM simulator; coverage report | Done |
| 14 | SCRUM-51 | Demo screenshots, Week 2 report, PPT draft v1 | This report |

## 3. Metrics
- Pull requests merged into `develop`: 13, all reviewed, CI green
- Automated tests: 41 (34 unit + 7 integration) — run on every push/PR
- Coverage: crypto + KM modules ≈ 91 %; total 67 % (email clients need a live mailbox; manual E2E checklist covers GUI)
- Security levels working end-to-end: 3 of 4

## 4. Demo evidence (screenshots in `docs/demo/`)
1. Inbox with live key indicator (96/100 keys)
2. Level 2 mail: ciphertext in Gmail web vs decrypted in QuMail with image preview
3. Level 3 mail decrypted (QK0003, 1,024 key bytes); 5.7 MB attachment blocked pre-send with key-length message
4. Key bank EMPTY state; compose with only Level 1; KM offline state
5. GitHub Actions run green; coverage table

## 5. Issues & resolutions
| Issue | Resolution |
|---|---|
| Avast Mail Shield rewrites mails (footer/headers), drops idle IMAP sockets, kills large SMTP uploads | Envelope parser ignores trailing text; IMAP auto-reconnect; keep L3 attachments small; disable Mail Shield for demos |
| 100 × 1 KB key bank too small for OTP with real attachments | Pre-send capacity check with exact byte/key numbers; Level 2 recommended for large files |
| Failed send left a key reserved forever | `burn_key` marks it consumed; typed KM errors (NoKeysAvailable / KeyConsumed / KMUnreachable) |
| KM simulator README says port 8000, Flask runs on 5000 | Client defaults to 5000; README fix requested |
| `keybank.csv` (key material) was committed | Removed from git, ignored |

## 6. Risks
- Key not auto-consumed after decrypt (deferred) — receiver can re-open a mail; to be decided with key-lifecycle review
- Level 4 design still open (prefer hybrid PQC via a maintained library over a custom cipher)
- Teammate activity on feature branches is low; crypto/KM work was absorbed by lead — re-balance Week 3 tasks

## 7. Plan for Week 3
Level 4 design + implementation, Yahoo/multi-account, UI polish and settings, security review (key lifecycle, logging), clean-machine install test prep.
