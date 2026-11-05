# Gmail / Yahoo edge cases — 2-step verification & app passwords (SCRUM-63)

Both providers refuse the normal account password over IMAP/SMTP. The client must therefore guide the
user to a **16-character app password**, which exists only after **2-step verification (2FA)** is on.
`src/qumail/email/auth_help.py` maps every reply we observed to one actionable sentence and the right
help link; the login screen also fixes two mistakes silently (pasted spaces, wrong provider).

## Test matrix

| # | Case | Provider | Server reply (raw) | What QuMail now shows | Result |
|---|---|---|---|---|---|
| 1 | 2FA **on**, user types normal password | Gmail | `[ALERT] Application-specific password required` | "2-step verification is ON, so Gmail needs an app password — not your normal password." + link to *App passwords* | ✅ |
| 2 | 2FA **off**, normal password | Gmail | `[AUTHENTICATIONFAILED] Invalid credentials (Failure)` | "Gmail does not accept the account password here. Turn on 2-step verification, create a 16-character app password…" | ✅ |
| 3 | Wrong / revoked app password | Gmail | `[AUTHENTICATIONFAILED] Invalid credentials` | "Gmail rejected the app password. Generate a new one…" | ✅ |
| 4 | App password pasted **with spaces** (`abcd efgh ijkl mnop`) | both | – | spaces removed before login; logs in | ✅ |
| 5 | Leading/trailing space in e-mail | both | – | trimmed | ✅ |
| 6 | Gmail address but **Yahoo** selected (or vice-versa) | both | – | provider switched automatically, message shown, user presses Sign in again | ✅ |
| 7 | Yahoo normal password | Yahoo | `[AUTHENTICATIONFAILED] LOGIN failed` | app-password advice + link to *Account security* | ✅ |
| 8 | Yahoo app password (Account security → Generate app password) | Yahoo | – | logs in; send + receive Level 1/2 | ⏳ verify with a Yahoo account |
| 9 | SMTP rejects after IMAP succeeded (app password revoked between) | Gmail | `535-5.7.8 Username and Password not accepted` | same advice at send time | ✅ |
| 10 | "Web login required" (new device / suspicious sign-in) | Gmail | `[ALERT] Web login required` | "Open Gmail in a browser once, approve the security alert, then retry." | ✅ |
| 11 | Account temporarily locked (many failures) | both | `Too many …` | "Wait 10–15 minutes." | ✅ |
| 12 | No internet | both | `getaddrinfo failed` | "No internet connection…" | ✅ |
| 13 | Port 993/465 blocked / antivirus | both | `timed out` / `CERTIFICATE_VERIFY_FAILED` | firewall / Mail Shield hint | ✅ |
| 14 | IMAP disabled in mailbox settings | Gmail | `IMAP access is disabled` | "enable it in Settings → Forwarding and POP/IMAP" | ✅ |
| 15 | Help link | both | – | "How to create an app password?" opens the provider's page in the browser | ✅ |

✅ = covered by `tests/test_auth_help.py` (server replies reproduced from real sessions) and checked manually on Gmail.
⏳ = needs a Yahoo account with 2FA; the code path is identical to Gmail (same IMAP/SMTP calls, different host).

## Notes for the report

- Google removed "less secure app access" in 2024 and Yahoo in 2023 — app passwords are now the **only** way
  for a third-party IMAP/SMTP client. This is why QuMail never asks for, stores or transmits the account password.
- App passwords are tied to the account's 2FA state: turning 2FA off revokes them all (case 3).
- Nothing in this module touches the password beyond removing whitespace; it is kept in memory only.
