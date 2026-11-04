# Performance test — large attachments & OTP key exhaustion

**Scope.** Time the crypto pipeline (`pipeline.prepare` → `pipeline.open_message`) for each security
level with attachments from 1 KB up to the 15 MB per-file limit, and show what happens when the
Key Manager's bank of 100 × 1 KB quantum keys runs out. The in-memory `FakeKM` is used so network
and Gmail latency are excluded; end-to-end sending over Gmail adds 2–8 s per MB depending on the link.

**How to run**

```cmd
python -m pytest -m perf -q            # pass/fail against generous budgets  (tests/perf/)
python tools/perf_report.py --write    # measure on this machine and refresh the table below
```

## Results

<!-- perf-table-start -->
| Payload | Level | Encrypt | Decrypt | Keys used |
|---|---|---|---|---|
| 1 KB | Level 2 AES-256-GCM | 1 ms | 1 ms | 1 |
| 1 KB | Level 4 double layer | 1 ms | 1 ms | 1 |
| 1 KB | Level 3 hybrid | 1 ms | 1 ms | 2 |
| 100 KB | Level 2 AES-256-GCM | 1 ms | 1 ms | 1 |
| 100 KB | Level 4 double layer | 2 ms | 1 ms | 1 |
| 100 KB | Level 3 hybrid | 1 ms | 1 ms | 2 |
| 1 MB | Level 2 AES-256-GCM | 2 ms | 2 ms | 1 |
| 1 MB | Level 4 double layer | 5 ms | 5 ms | 1 |
| 1 MB | Level 3 hybrid | 2 ms | 2 ms | 2 |
| 5 MB | Level 2 AES-256-GCM | 8 ms | 6 ms | 1 |
| 5 MB | Level 4 double layer | 24 ms | 23 ms | 1 |
| 5 MB | Level 3 hybrid | 7 ms | 6 ms | 2 |
| 15 MB | Level 2 AES-256-GCM | 31 ms | 22 ms | 1 |
| 15 MB | Level 4 double layer | 98 ms | 99 ms | 1 |
| 15 MB | Level 3 hybrid | 28 ms | 22 ms | 2 |

OTP exhaustion: 100 Level-3 mails (900 B each) drained a 100 × 1 KB bank in 55 ms; the 101st was blocked by check_capacity before any key was requested.

Machine: Windows-11-10.0.26200-SP0 · Python 3.13.14 · 04 Nov 2026 19:42
<!-- perf-table-end -->

## Observations

1. **Levels 2 and 4 scale linearly and stay well under a second even at 15 MB** — AES-GCM and
   ChaCha20-Poly1305 are stream-style ciphers; Level 4 costs roughly 2× Level 2 because the data
   is encrypted twice. Both use exactly **one** 1 KB quantum key per mail, independent of size.
2. **Level 3 (One-Time Pad) is bound by key, not CPU.** XOR itself is the fastest operation in the
   table, but the key must be as long as the payload: a 60 KB file consumes 60 of the 100 keys.
   Pure OTP is therefore only practical for short text; **Hybrid** (OTP body + AES attachments)
   keeps perfect secrecy for the text and costs 2 keys regardless of attachment size.
3. **Exhaustion is handled before a key is wasted.** `check_capacity()` compares the required key
   bytes with the KM's `available × key_size` and refuses with a human message
   ("Not enough quantum key … Tip: enable Hybrid or use Level 2"); the KM additionally answers
   HTTP 409. After the bank is empty only Level 1 is offered in the Compose dropdown.
4. **Failed sends burn their key** (`burn_key`), so a reserved key is never reused — consistent with
   the one-time property verified in SCRUM-64.
5. **Envelope overhead** (JSON + base64) is < 1.4× for text; attachments are sent as binary `.qenc`
   parts, so MIME base64 is the only overhead (+33 %), hence the 18 MB raw / 25 MB provider budget.

## Recommendations

- Keep the default Level for attachments at 2 (or 4); surface the Hybrid tick box automatically
  when Level 3 is chosen with files (already implemented, SCRUM-54).
- A production KM should offer larger or streaming keys for OTP; with 1 KB keys, OTP of anything
  above ~50 KB is impractical (hence `QUMAIL_LEVEL3_WARN_KB=50`).
