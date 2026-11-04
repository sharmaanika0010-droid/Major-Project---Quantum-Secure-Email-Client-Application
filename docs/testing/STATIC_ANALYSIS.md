# Static analysis

Three tools run on every push and pull request (`.github/workflows/ci.yml`, job **Static analysis**).
The job is *required*, so a finding blocks the merge.

| Tool | What it checks | Config |
|---|---|---|
| **ruff** | style, unused imports, import order, bug-prone patterns (`E F W I B`) | `ruff.toml` |
| **bandit** | security anti-patterns: hard-coded passwords, `eval`, weak hashes, insecure temp files, `try/except/pass`, unsafe URL schemes … | `bandit.yaml` |
| **pip-audit** | known CVEs in the pinned dependencies (`requirements.txt`) | – |

Run locally:

```cmd
python -m ruff check src tests
python -m bandit -c bandit.yaml -r src
python -m pip_audit -r requirements.txt
```

## Baseline (first run) and what was done

| Finding | Where | Action |
|---|---|---|
| B413 ×10 *PyCrypto deprecated* | `Crypto.Cipher`, `Crypto.Hash`, `Crypto.Protocol` imports | **False positive** — the project uses **pycryptodome**, which lives in the same `Crypto` namespace. Skipped in `bandit.yaml` with justification. |
| B310 *urlopen with custom scheme* | `src/crypto/level2.py` (prototype KM client) | Scheme is now validated: only `http://`/`https://` URLs are accepted. |
| B107 *possible hard-coded password `token.json`* | `src/email_service/gmail_adapter.py` | File *name*, not a secret — annotated `# nosec B107`. The file itself is git-ignored. |
| B110 *try/except/pass* | `src/qumail/gui/compose.py` | Replaced by `contextlib.suppress` with a comment explaining why the failure is non-fatal. |
| pip-audit | `requirements.txt` | No known vulnerabilities. |

Result after fixes: **bandit 0 issues · ruff 0 issues · pip-audit 0 vulnerabilities.**

## Why ESLint / SonarQube were not used

The plan named ESLint/SonarQube. ESLint only analyses JavaScript; QuMail is pure Python,
so the Python equivalents were used instead. SonarQube needs a hosted server (or SonarCloud
account with organisation setup) — bandit + ruff + pip-audit give the same classes of checks
inside GitHub Actions with zero infrastructure, which fits a student project better.
