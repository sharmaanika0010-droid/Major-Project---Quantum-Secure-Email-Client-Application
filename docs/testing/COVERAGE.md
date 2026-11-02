# QuMail — Test Coverage Report

Ticket: SCRUM-45 · Day 12 · Generated locally with `pytest --cov` (unit + integration, KM simulator running in-process).
The CI job **"Integration (KM simulator) + coverage"** regenerates this on every push — see the job *Summary* and the `coverage-report` artifact (HTML).

## How to reproduce
```
python -m pip install -r requirements-dev.txt
python -m pytest -q -m "not live" --cov --cov-report=term-missing --cov-report=html
start htmlcov\index.html
```

## Result (41 tests: 34 unit + 7 integration, all passing)
| Module | Stmts | Miss | Cover | Notes |
|---|---|---|---|---|
| crypto/envelope.py | 59 | 5 | **91.5 %** | uncovered: missing-dependency warnings |
| crypto/level2.py | 48 | 5 | **89.6 %** | uncovered: malformed-blob guards |
| crypto/level3.py | 56 | 4 | **92.9 %** | uncovered: malformed-blob guards |
| crypto/pipeline.py | 75 | 5 | **93.3 %** | uncovered: unreadable attachment path |
| km/client.py | 64 | 7 | **89.1 %** | uncovered: 422 / non-JSON error paths |
| email/imap_client.py | 167 | 112 | 32.9 % | needs a live mailbox → `live` marker |
| email/smtp_client.py | 44 | 31 | 29.5 % | needs a live mailbox → `live` marker |
| **TOTAL** | **513** | **169** | **67.1 %** | crypto + KM ≈ **91 %** (target ≥ 80 % ✅) |

GUI modules (`gui/*`) are excluded (`.coveragerc`) — covered by the manual E2E checklist in TEST_PLAN.md §6.

## Integration flow covered (tests/integration/test_level3_flow.py)
1. Sender: `check_capacity` → `prepare(level 3, body, attachment)` — keys reserved in the **real** KM simulator (fresh bank per run, random free port).
2. Transport: a real MIME message is built and parsed back from bytes; asserted that neither the body nor the attachment appears in plaintext on the wire, headers `X-QuMail-Level: 3` / `X-QuMail-KeyID` present.
3. Receiver: `open_message` fetches the key by ID from KM → body matches, attachment SHA-256 matches.
4. Negative paths: key-id tampering rejected (MAC), burned key → `KeyConsumed`, oversize attachment blocked with nothing reserved, drained bank → `NoKeysAvailable`.
5. `test_live_email.py` — optional end-to-end through Gmail (skipped without `QUMAIL_TEST_EMAIL` / `QUMAIL_TEST_PASSWORD`); run before demos.
