# Regression Test Report — QuMail v1.0 candidate (SCRUM-68)

| | |
|---|---|
| Build under test | `develop` @ `80c82b7` (after PR #29 — all Day 1–19 tickets merged) |
| Run date | 05 Nov 2026 |
| Environments | Windows 11 / Python 3.12 (developer PC, local run) · Ubuntu / Python 3.11 & 3.13 (GitHub Actions CI) |
| How to reproduce | `scripts\run_regression.bat` (Windows) or `scripts/run_regression.sh` — writes `reports/regression_<date>.txt` |
| Verdict | **PASS — 0 failures, 0 open S1/S2 defects. Release candidate accepted.** |

## 1. Summary

| Suite | Command | Tests | Passed | Failed | Skipped | Time |
|---|---|---|---|---|---|---|
| Static analysis | `ruff check src tests` · `bandit -c bandit.yaml -r src` · `pip-audit` | — | clean | 0 findings | — | ~10 s |
| Unit (default) | `python -m pytest -q` | 163 | **162** | 0 | 1 (live mailbox, needs credentials) | 0.8 s |
| Integration — real KM simulator | `pytest -m integration` | 9 | **9** | 0 | 0 | 0.5 s |
| Performance | `pytest -m perf` | 14 | **14** | 0 | 0 | 0.8 s |
| Manual E2E (TEST_PLAN §6) | exe build, Gmail ×2 | 9 steps | **9** | 0 | 0 | ~25 min |
| **Total automated** | | **186** | **185** | **0** | **1** | |

Coverage (unit + integration, `--cov=src/qumail`): **80.7 %** of 1 037 statements. Crypto core
(level2/3/4, envelope, pipeline, km client) 87–98 %; IMAP/SMTP clients 35–43 % (network paths are
covered by the manual E2E and the `live` test, see COVERAGE.md).

## 2. Unit suite by module (what each file regresses)

| File | Tests | Covers |
|---|---|---|
| test_aes.py | 15 | AES-256-GCM primitives, tag/nonce handling (legacy prototype + current) |
| test_level2.py · test_level2_qumail.py | 5 + 6 | Level 2 HKDF derivation, encrypt/decrypt, attachments `.qenc`, tamper → error |
| test_level3.py | 6 | OTP body + attachments, key-too-short error, HMAC integrity |
| test_level4.py | 8 | AES-GCM + ChaCha20-Poly1305 double layer, independent sub-keys, tamper |
| test_envelope.py | 5 | JSON envelope format, headers `X-QuMail-Level/KeyID`, Level 1 passthrough |
| test_pipeline.py | 11 | prepare / open_message for L1–L4, hybrid L3, burn_key, capacity check |
| test_limits_and_hybrid.py | 12 | attachment size / count limits, hybrid key accounting |
| test_otp_no_reuse.py | 17 | SCRUM-64 — one-time key properties P1–P7, read-once flag |
| test_wrong_km.py | 10 | SCRUM-67 — key fingerprint, different-KM detection, legacy mails |
| test_km_client.py | 6 | KM REST client: 409/410/404 mapping, unreachable |
| test_config.py | 13 | `.env` loading, defaults, no hard-coded secrets/URLs in source |
| test_contacts.py | 8 | address book CRUD, preferred level, remember-after-send |
| test_audit.py | 7 | hash-chained audit log, no key material logged, chain verification |
| test_auth_help.py | 16 | SCRUM-63 — provider detection, app-password normalisation, error explanations |
| test_smtp_sender.py | 2 | MIME construction, headers |
| test_ui_helpers.py | 6 | date/sender formatting, ellipsis, multi-recipient parsing |
| integration/test_level3_flow.py | 7 | full L2/L3 flow against the Flask simulator incl. attachment, wrong key, burned key |
| integration/test_km_no_reuse.py | 2 | simulator never re-issues a key; over-request refused |
| integration/test_live_email.py | 1 | real Gmail round-trip (skipped without credentials) |
| perf/* | 14 | 5 MB attachments per level, OTP exhaustion prediction, envelope overhead, failed-send burn |

## 3. Regression of fixed defects (bug bash + edge cases)

| Defect | Regression test | Result |
|---|---|---|
| BB-01 list row alignment | manual (exe) | ✅ |
| BB-02 empty mail reserved a key | manual: "Nothing to send" | ✅ |
| BB-03 multi-recipient contact | `test_parse_recipients_splits_and_validates` | ✅ |
| BB-04 hard truncation | `test_ellipsize_adds_visible_ellipsis` | ✅ |
| BB-07 wrong KM → "Integrity check failed" | `test_wrong_key_manager_gives_clear_message` (×3 levels) | ✅ |
| E1–E15 login edge cases (SCRUM-63) | test_auth_help.py | ✅ |
| Key reuse (SCRUM-64 review) | test_otp_no_reuse.py, integration/test_km_no_reuse.py | ✅ |
| Key exhaustion with attachments (SCRUM-61) | perf/test_otp_exhaustion_is_predicted_and_blocked | ✅ |
| Duplicate inbox render on double refresh (SCRUM-60) | manual | ✅ |

## 4. Manual E2E checklist (TEST_PLAN §6) — exe build

| # | Step | Result |
|---|---|---|
| 1 | Gmail login with app password, inbox loads | ✅ 18 messages |
| 2 | KM indicator green with count; KM stopped → red "offline" | ✅ |
| 3 | L1 send → received with `X-QuMail-Level: 1` | ✅ |
| 4 | L2 + image → ciphertext in Gmail, decrypted + preview in QuMail | ✅ |
| 5 | L3 small + txt decrypts; L3 with 5 MB blocked with key-length message | ✅ |
| 6 | Bank drained → EMPTY, Level 1 fallback offered | ✅ |
| 7 | Re-open mail after key consumed → "already consumed" | ✅ |
| 8 | Yahoo: steps 1, 3, 4 | ✅ |
| 9 | Downloaded attachment byte-identical (hash) | ✅ |

## 5. Known limitations carried into release (not regressions)

- Avast Mail Shield drops idle IMAP / kills large SMTP uploads (BB-09/10) — documented workaround.
- A failed send burns the reserved key by design (BB-06).
- Simulator stores keys in clear text `keybank.csv` — out of scope (real KM = ETSI QKD 014 hardware).
- `live` mailbox test runs only with `QUMAIL_TEST_EMAIL/PASSWORD` set.

## 6. Sign-off

Regression suite green on Windows (local) and Linux (CI, Python 3.11 + 3.13). No S1/S2 defects
open. Build `80c82b7` is accepted as the demo / submission candidate; the exe must be rebuilt
from this commit with `packaging\build_exe.bat` before the final demo.
