# Live regression matrix — all levels × providers × attachments (SCRUM-69)

Complements `REGRESSION_REPORT.md` (automated suites) with the **real-mailbox** matrix the unit
tests cannot cover: SMTP/IMAP against Gmail and Yahoo, every security level, with and without
attachments. Each cell is one send-and-read-back round trip through the provider.

## How it is run

`tests/integration/test_live_email.py` (marker `live`) sends a mail to the test account, polls the
inbox until it arrives, decrypts it with the running KM simulator and checks body + attachment
bytes. Provider is detected from the address. One command per provider:

```
scripts\live_regression.bat        ← asks for account + app password, saves reports\live_<account>_<time>.txt
```
Prerequisites: KM simulator running (`src\km_simulator\km_simulator.py` or `QuMail-KM.exe`), app
password for the account, Avast Mail Shield off (see EMAIL_EDGE_CASES E11/E12).

Each run = 9 cases: L1–L4 text only, L1–L4 with a text attachment, L3 hybrid with a 60 KB binary.
Key cost per run: L2 1 key, L3 ≤ 1 key, L4 1 key, hybrid 2 keys → **≈ 8 keys per provider**.

## Results

Build: `develop @ 80c82b7` · Date: 06 Nov 2026 · KM: simulator, 100 × 1 KB keys · Account: qumailtest71@gmail.com

| Case | Level | Attachment | Gmail | Yahoo | Notes |
|---|---|---|---|---|---|
| 1 | 1 — plain | none | ✅ | n/a – no Yahoo account | header `X-QuMail-Level: 1` |
| 2 | 1 — plain | .txt | ✅ | n/a | attachment passes through unchanged |
| 3 | 2 — AES-256-GCM | none | ✅ | n/a | |
| 4 | 2 — AES-256-GCM | .txt → `.qenc` | ✅ | n/a | decrypted bytes identical |
| 5 | 3 — OTP | none | ✅ | n/a | |
| 6 | 3 — OTP | .txt (≈700 B) | ✅ | n/a | body + file within one 1 KB key |
| 7 | 3 — OTP hybrid | 60 KB binary | ✅ | n/a | OTP body + AES attachment, 2 keys |
| 8 | 4 — double layer | none | ✅ | n/a | |
| 9 | 4 — double layer | .txt → `.qenc` | ✅ | n/a | |
| — | Static analysis | — | ✅ | — | from REGRESSION_REPORT.md |
| — | Unit + integration + perf | — | ✅ 185 | — | from REGRESSION_REPORT.md |

Gmail run: `9 passed in 133.13s (0:02:13)` — log `reports/live_qumailtest71@gmail.com_2026-11-06_0920.txt`
(attached to SCRUM-69). Yahoo: not run — no Yahoo test account available; Yahoo login/edge cases are
covered by `EMAIL_EDGE_CASES.md` and `test_auth_help.py`.

## Defects found during this run

| ID | Case | Description | Fixed in |
|---|---|---|---|
| RM-01 | all | `test_live_email.py` constructed `IMAPClient(EMAIL, PASSWORD)` / `SMTPClient(EMAIL, PASSWORD)` without the `provider` argument (signature changed in SCRUM-60) – the test was always skipped in CI so this was never caught. Also used `smtp.connect()/close()` which do not exist. | this ticket |
| | | | |

## Checklist before marking Done

- [x] Gmail run: 9 passed, log attached
- [x] Yahoo run: n/a – no Yahoo account available
- [x] Any ❌ logged above and in Jira as a Bug (none found)
- [x] Build/commit and date filled in