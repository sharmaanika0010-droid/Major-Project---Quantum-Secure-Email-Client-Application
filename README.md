# QuMail — Quantum Secure Email Client

Desktop email client that works with ordinary Gmail / Yahoo accounts and protects each message with keys from a Quantum Key Manager (KM). The sender picks a security level per mail; the mail provider only ever sees ciphertext.

| Level | Mechanism | Key usage |
|---|---|---|
| 1 | Plain text | none |
| 2 | AES-256-GCM, key derived from a quantum key (HKDF) | one 1 KB key per mail |
| 3 | One-Time Pad + HMAC-SHA256 | key ≥ text + attachments |
| 3 Hybrid | OTP for the text, AES-256-GCM for attachments | ~1 KB + text length |
| 4 | Double layer: AES-256-GCM then ChaCha20-Poly1305 (two HKDF keys from one quantum key) | one 1 KB key per mail |

Team: Anika Sharma (lead, architecture, DevOps) · Amit Chouhan (email, GUI) · Umang Goswami (crypto, KM, testing)
Tracker: Jira project `SCRUM` · Branches: `main` (releases), `develop` (integration), `feature/*`

## Quick start (Windows)

```cmd
git clone https://github.com/sharmaanika0010-droid/Major-Project---Quantum-Secure-Email-Client-Application.git
cd Major-Project---Quantum-Secure-Email-Client-Application
python -m pip install -r requirements.txt
```

1. Start the Key Manager simulator (keeps running, port 5000):
   ```cmd
   python src\km_simulator\km_simulator.py
   ```
2. Start QuMail in a second window:
   ```cmd
   cd src
   python -m qumail.gui.app
   ```
3. Log in with your Gmail address and an **app password** (Google account → Security → 2-Step Verification → App passwords). Yahoo: generate an app password under Account Security.

## Configuration (.env)

No value is hard-coded. Copy `.env.example` to `.env` (git-ignored) and change what you need — every variable is optional:

| Variable | Default | Meaning |
|---|---|---|
| `QUMAIL_EMAIL` / `QUMAIL_PROVIDER` | – / `Gmail` | pre-filled on the login screen |
| `QUMAIL_KM_URL` / `QUMAIL_KM_TIMEOUT` | `http://localhost:5000` / `5` | Key Manager address and timeout (s) |
| `QUMAIL_SMTP_PORT` / `QUMAIL_SMTP_TIMEOUT` / `QUMAIL_IMAP_TIMEOUT` | `465` / `30` / `30` | mail transport |
| `QUMAIL_MAX_FILES` / `QUMAIL_MAX_FILE_MB` / `QUMAIL_MAX_TOTAL_MB` | `10` / `15` / `18` | attachment limits |
| `QUMAIL_LEVEL3_WARN_KB` | `50` | warn before OTP on big files |

The mail password is **never** stored in `.env` or anywhere on disk — it is typed at login and kept in memory only. `tests/test_config.py` fails the build if `.env`, `credentials.json`, `token.json` or `keybank.csv` is ever committed, or if a KM URL / app password appears in the code.

## Using it

- **Compose** → choose *Security level* → write → *Attach* (multiple files, up to 10 / 15 MB each / 18 MB total) → *Send*.
- The top bar shows the live key bank (`🔑 96/100 quantum keys`). When the bank is empty or the KM is offline only Level 1 is offered.
- Level 3 with large files is blocked before sending if not enough key material exists; tick **Hybrid** to keep OTP for the text and use AES for the files.
- Received encrypted mails show a badge (L2 / L3) and are decrypted with the key referenced in the `X-QuMail-KeyID` header. In Gmail's web UI the same mail is an unreadable JSON envelope with `.qenc` attachments.

## Project layout

```
src/qumail/
  gui/        login, inbox, compose (CustomTkinter)
  crypto/     envelope format, level2 (AES-GCM), level3 (OTP), pipeline, limits
  km/         Key Manager REST client
  email/      IMAP and SMTP clients
tests/        unit tests (fake KM) and integration tests (real KM simulator)
docs/         diagrams, test plan, coverage, reports, demo screenshots
src/km_simulator/km_simulator.py   Flask Key Manager simulator (100 × 1 KB keys)
src/crypto, src/email_service, src/app.py
                                   Streamlit prototype of Level 1/2 (crypto & email team) — standalone demo,
                                   run with `streamlit run src/app.py`; the desktop client above is the main product
SCRUM_Docs/, SVVV_Documentation/   UML diagrams, SRS/synopsis templates, per-ticket notes
.github/workflows/ci.yml           lint + tests on every push / PR
```

## Development

```cmd
python -m pip install -r requirements-dev.txt
python -m pytest -q                    # unit + integration (starts the KM simulator itself)
python -m ruff check src tests         # lint
```

Workflow: Jira ticket → `feature/SCRUM-<id>-<name>` branch → pull request to `develop` → CI green + review → merge. Commit messages start with the ticket id.

## Notes and limitations

- The KM simulator holds 100 keys of 1 KB; delete `src/km_simulator/keybank.csv` and restart to reset it (previously sent encrypted mails can then no longer be opened).
- Antivirus mail shields (e.g. Avast) rewrite mails and can break large uploads — disable them while testing.
- Keys are reserved when a mail is prepared and burned if sending fails; automatic consumption after decryption is still open.
