# Demo screenshots — capture checklist

Save as PNG in this folder with these exact names (used by the PPT and reports). Window ≈ 1400×800, dark theme, KM simulator running.

| # | File | What to show | How |
|---|---|---|---|
| 1 | `01_login.png` | Login screen | Start app |
| 2 | `02_inbox_keys.png` | Inbox, green "🔑 N/100 quantum keys", L2/L3 badges | Login → inbox |
| 3 | `03_compose_l2.png` | Compose, Level 2 selected, image attached | Compose → Level 2 → Attach |
| 4 | `04_gmail_ciphertext.png` | Same mail in Gmail web: JSON envelope + `.qenc` | Open mail.google.com |
| 5 | `05_l2_decrypted.png` | QuMail: "🔓 Decrypted with quantum key QK…", image preview | Click the mail |
| 6 | `06_l3_decrypted.png` | Level 3 mail decrypted with key-bytes note | Send small .txt at Level 3 |
| 7 | `07_l3_blocked.png` | "Not enough quantum key: Level 3 needs … bytes" | Attach 5 MB file at Level 3 → Send |
| 8 | `08_bank_empty.png` | Red "Key bank EMPTY (0/100) — only Level 1 possible" | Drain via `/keys/request` → Refresh |
| 9 | `09_compose_l1_only.png` | Compose with only Level 1 in dropdown | Compose while empty |
| 10 | `10_km_offline.png` | Red "KM offline" in inbox | Stop simulator → Refresh |
| 11 | `11_ci_green.png` | GitHub Actions run with 3 green checks | Actions tab |
| 12 | `12_coverage.png` | Coverage table (terminal or htmlcov) | `python -m pytest --cov` |

Reset after 8–10: stop simulator, delete `SCRUM_Works/SCRUM-14/keybank.csv`, restart (old L2/L3 mails won't open — send fresh ones for 5–6).
