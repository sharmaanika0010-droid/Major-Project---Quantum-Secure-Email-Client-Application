# QuMail — Test Plan (v1)

Ticket: SCRUM-40 · Date: 08 Oct 2026 · Owner: QA (Umang) / DevOps (Anika)

## 1. Scope
QuMail desktop client: email (IMAP/SMTP), Key Manager (KM) client, crypto levels 1–3 (4 planned), GUI.
Out of scope for automated tests: real Gmail/Yahoo servers, the Tk GUI (manual).

## 2. Test levels
| Level | What | Tool | When |
|---|---|---|---|
| Unit | envelope, level2 (AES-GCM), level3 (OTP), pipeline, KM client | pytest (+ FakeKM, fake requests) | every push / PR (CI) |
| Integration | KM simulator ↔ client, send/receive via real Gmail test account | manual + scripts | before each sprint demo |
| System / E2E | Full flows in GUI (login → compose → send → receive → decrypt) | manual checklist (§6) | Day 14, 21, 26, 28 |
| Security | wrong key, tampering, key reuse, depleted bank | pytest + manual | CI + Day 20 |
| Clean-machine | fresh Windows, no Python deps pre-installed | manual | Day 26 |

## 3. CI pipeline (GitHub Actions — `.github/workflows/ci.yml`)
- Triggers: push to `main`, `develop`, `feature/**`, `chore/**`; PRs to `main`/`develop`.
- Matrix: Python 3.11 and 3.13 on ubuntu-latest.
- Steps: install `requirements.txt` → `ruff check` (lint) → `pytest --cov=qumail` → coverage artifact.
- Rule: a PR cannot be merged with a red check (enable "Require status checks" on `develop`).

## 4. Running locally
```
pip install -r requirements.txt pytest pytest-cov ruff
pytest -q                 # unit tests (no KM / network needed)
ruff check src tests      # lint
```

## 5. Unit test matrix (current)
| Module | Cases |
|---|---|
| `crypto/envelope.py` | levels registered; L1 roundtrip; envelope parse ignores footers; rejects plain text; unknown level |
| `crypto/level2.py` | roundtrip; wrong key; tampered ciphertext; fresh nonce per message; attachment bytes; HKDF deterministic 256-bit |
| `crypto/level3.py` | roundtrip with attachments; key length incl. MAC; key too short; wrong key; tampered attachment; no key-byte overlap |
| `crypto/pipeline.py` | L1/L2/L3 send→open roundtrip; L3 reserves ceil(bytes/1KB) keys; capacity check blocks oversized L3, allows L2; empty bank; KM offline; burn key on failure; missing key id |
| `km/client.py` | status/available_bytes; multi-key join; 409 → NoKeysAvailable; 410 → KeyConsumed; 404 → KMError; consume splits ids; connection error → KMUnreachable |

Coverage target: ≥ 80 % on `src/qumail/crypto` and `src/qumail/km`. GUI modules excluded.

## 6. Manual E2E checklist (per release)
1. Login Gmail with app password → inbox loads (≤ 5 s for 25 headers).
2. KM Test button → green with key count; stop KM → red "offline".
3. Compose L1 → received in Gmail with `X-QuMail-Level: 1`.
4. Compose L2 + image → Gmail shows ciphertext JSON + `.qenc`; QuMail decrypts, preview works.
5. Compose L3 small + txt → decrypted; L3 with 5 MB file → blocked with key-length message.
6. Drain bank → EMPTY state, only L1 in selector; "Send as Level 1 instead" works.
7. Re-open L2 mail after key consumed → clear "already consumed" error.
8. Yahoo account: steps 1, 3, 4.
9. Attachment download writes identical bytes (compare hash).

## 7. Defect handling
Bugs → Jira type *Bug*, linked to the day's ticket, priority High if data loss / decrypt failure. Fix via PR with a regression test.
