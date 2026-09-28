# QuMail — Quantum Secure Email Client

Desktop email client that encrypts Gmail/Yahoo emails using quantum keys from a Key Manager (QKD).
Security levels: 1 (None) · 2 (Quantum-aided AES) · 3 (One-Time Pad) · 4 (Extra)

Team: Anika Sharma (Lead, Architecture/DevOps) · Amit Chouhan (Email/GUI) · Umang Goswami (Crypto/KM)
Tracker: Jira project SCRUM · Docs: see docs/PROJECT_VISION.md

## Structure
- `src/qumail/` — crypto, km, email, gui modules
- `km_simulator/` — mock Key Manager REST API
- `tests/` — unit & integration tests
- `docs/` — UML diagrams, reports

## Setup
pip install -r requirements.txt
