# Deployment Diagram — QuMail (deployed setup) v1

Source: `deployment_diagram_v1.drawio` (open in app.diagrams.net) · export: `deployment_diagram_v1.png`

Matches the setup actually used for the demo: the Windows one-folder build from `packaging/build_exe.bat`
(see `docs/deploy/BUILD_EXE.md`), no Python installed on the target PCs.

## Nodes

| Node | Execution environment | Deployed components / artifacts |
|---|---|---|
| Sender PC (Windows 10/11) | `QuMail-GUI.exe` (PyInstaller, Python 3.12 runtime bundled) | GUI (customtkinter), Crypto Module (Level 1–4, envelope), KM Client, Mail clients (imaplib/smtplib), Config/Audit, Address Book; `START_QUMAIL.bat`; user data in `%USERPROFILE%\.qumail\` (`.env`, `contacts.json`, `audit.log`) |
| Key Manager host (same PC for demo, LAN server otherwise) | `QuMail-KM.exe` (Flask, port 5000) | KM Simulator REST API (`/keys/request`, `/keys/<id>`, `/keys/consume`, `/keys/status`), `keybank.csv` (100 × 1 KB keys with state), `km_simulator.log` |
| Email Provider (cloud) | Gmail / Yahoo | SMTP server, IMAP server — carries only ciphertext + `X-QuMail-*` headers |
| Receiver PC (Windows 10/11) | `QuMail-GUI.exe` (same build) | GUI inbox/read, Crypto Module (decrypt), KM Client (`GET /keys/<id>`) |
| GitHub | Actions CI | ruff + bandit, pytest, `QuMail-win.zip` exe artifact |

## Communication paths

| From → To | Protocol / port | Payload |
|---|---|---|
| KM Client → KM API | HTTP/REST, `localhost:5000` (demo) or LAN host | JSON, key material base64 |
| Mail client → SMTP | SMTP + STARTTLS 587 (or SSL 465) | encrypted envelope as mail body |
| Mail client → IMAP | IMAP over SSL 993 | fetch encrypted mails |
| Receiver KM Client → KM API | HTTP/REST, same KM host:5000 | key by id (RESERVED keys readable, CONSUMED → 410) |

## Constraints shown on the diagram

- Sender and receiver must use the **same Key Manager** (shared key bank); a different KM gives
  "Integrity check failed".
- Key states AVAILABLE → RESERVED → CONSUMED; a key is never re-issued (see
  `docs/security/OTP_KEY_REUSE_REVIEW.md`).
- The mail provider never sees plaintext or key material.
- Internet is required for SMTP/IMAP; the KM link stays local/LAN.

## Change log
- v1 — finalized to match the PyInstaller deployment (replaces the early plan-stage sketch).