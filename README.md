# QuMail — Quantum Secure Email Client Application

Email client that encrypts Gmail messages using quantum keys from a Key Manager (QKD). It works at the application layer: QuMail consumes pre-generated symmetric keys through a Key Manager API and does not implement physical QKD.

**Security levels:** 1 (No quantum security) · 2 (Quantum-aided AES) · 3 (One-Time Pad) · 4 (Extra, optional)

**Team:** Anika Sharma (Lead, Architecture/DevOps) · Amit Chouhan (Email/GUI) · [Umang Goswami](https://github.com/goswamiumang108) (Crypto/KM)
**Tracker:** Jira project SCRUM

## Current status

| Part | Status |
|---|---|
| Level 1: plain Gmail send/receive (Streamlit UI) | Done (SCRUM-17) |
| Key Manager simulator (100 × 1 KB keys, REST API, `/get_key`) | Done (SCRUM-14, SCRUM-20) |
| Level 2 AES, Level 3 OTP, Key Manager client | Not started |

## Structure

```
src/
├── app.py              Streamlit UI (Inbox + Compose)
├── email_service/      Email provider interface + Gmail adapter
├── km_simulator/       Mock Key Manager REST API (Flask)
├── crypto/             AES / OTP (planned)
└── gui/                UI modules (planned)
tests/                  Unit and integration tests
SCRUM_Docs/             Per-ticket docs, diagrams and research (docs only)
SVVV_Documentation/     College templates, schedules and guidelines
```

## Setup

```
pip install -r requirements.txt
```

All commands below are run from the repo root.

**1. Key Manager simulator** (runs at http://127.0.0.1:5000)
```
python src/km_simulator/km_simulator.py
```
On first run it generates `src/km_simulator/keybank.csv` (100 keys). The file holds secret key material and is gitignored. Never commit it.

**2. QuMail app**
```
streamlit run src/app.py
```
Place your own `credentials.json` (Google OAuth, "Desktop app" client, Gmail API enabled) in the repo root. A browser window opens for Google sign-in on first run and creates `token.json`. Never commit either file.

## Documentation

Ticket write-ups live in `SCRUM_Docs/SCRUM-<id>/`. Each has its own README with run steps and notes.