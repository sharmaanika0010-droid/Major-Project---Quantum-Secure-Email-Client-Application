# Security review — one-time use of quantum keys (SCRUM-64)

**Question.** Is a quantum key ever used twice? For a One-Time Pad this is the only thing that
matters: two messages XOR-ed with the same pad leak `m1 ⊕ m2` and the pad is broken. For the
AES/ChaCha levels, reusing a key *with the same nonce* is equally fatal.

**Scope.** `src/qumail/crypto/level3.py` (OTP), `level2.py`, `level4.py`, `pipeline.py`,
`km/client.py`, `src/km_simulator/km_simulator.py`. Reviewed by reading the code and by writing
the properties below as automated tests (`tests/test_otp_no_reuse.py`,
`tests/integration/test_km_no_reuse.py`).

## Key lifecycle

```
AVAILABLE ──request_key──► RESERVED ──consume──► CONSUMED
                              │                      ▲
                              │   send failed (burn_key)   │
                              └──────────────────────┘
```

| Step | Who | Guarantee |
|---|---|---|
| `POST /keys/request` | sender | only AVAILABLE keys are returned; they become RESERVED atomically (`threading.Lock`) |
| encrypt | sender | OTP: body = key[0:n], attachment *i* = next slice, MAC key = key[total:total+32] — **disjoint, contiguous, each byte once** (test P3) |
| send fails | sender | `burn_key()` → CONSUMED; never returns to the pool (P2) |
| `GET /keys/<id>` | receiver | RESERVED keys can be read (needed to decrypt); CONSUMED → **410** |
| open mail | receiver | optional `QUMAIL_CONSUME_AFTER_DECRYPT=1` → key CONSUMED after first successful read |

## Properties verified by tests

| # | Property | Test |
|---|---|---|
| P1 | every send gets key ids never issued before (Levels 2/3/4) | `test_every_send_uses_fresh_key_ids` |
| P2 | burned key is never issued again and cannot be read back | `test_burned_key_is_never_issued_again` |
| P3 | inside one OTP message no key byte is used twice | `test_level3_key_slices_are_disjoint_and_cover_once` |
| P4 | hybrid mode uses two distinct keys | `test_hybrid_uses_two_distinct_keys` |
| P5 | AES-GCM / ChaCha20 get a fresh 96-bit nonce from `secrets` every time | `test_aes_levels_use_fresh_nonce_per_message` |
| P6 | a wrong key of the right length fails MAC/GCM — no silent garbage | `test_wrong_key_of_same_length_never_decrypts`, `test_level3_tampered_ciphertext_is_detected` |
| P7 | empty bank blocks every encrypted level before a key is requested | `test_exhausted_bank_blocks_all_encrypted_levels` |
| KM | real simulator never re-issues, 410 after consume, 409 when empty | `tests/integration/test_km_no_reuse.py` |

## Findings

| ID | Severity | Finding | Status |
|---|---|---|---|
| F1 | — | **No key reuse for encryption was found.** The pool only ever hands out AVAILABLE keys and nothing moves a key back to AVAILABLE. | ✅ confirmed |
| F2 | Low | OTP key shorter than payload: `encrypt` raises *before* any XOR; `_xor` uses `zip(strict=False)` which would otherwise silently truncate. The guard is the only thing preventing a short pad. | ✅ covered by `test_level3_rejects_key_shorter_than_payload`; keep the guard |
| F3 | Low | Attachment offsets are read from the blob (attacker controlled). An attacker could point them into another slice. | ✅ safe — the HMAC covers the offset bytes, so any change fails the integrity check (P6) |
| F4 | Info | After a successful send the key stays RESERVED forever (it is never CONSUMED) because the receiver still has to fetch it. It is never re-issued, so this is not a reuse — but the KM cannot distinguish "in transit" from "read". | ➕ added `QUMAIL_CONSUME_AFTER_DECRYPT` (default off): receiver burns the key on first read → true read-once. Off by default because a user then cannot re-open the mail (the app does not cache plaintext). |
| F5 | Info | Level 2/4 derive a 256-bit key from the first 32/64 bytes of a 1 KB quantum key; the rest is unused. Not a reuse issue, only key efficiency. | documented in PERFORMANCE.md |
| F6 | Info | HKDF `info` strings differ per level ("qumail-level2-aes" vs "qumail-level4-…") so the same raw key could never yield the same AES key for two levels — and the KM never gives the same raw key twice anyway. | ✅ |

## Residual risks / out of scope

- The simulator stores key material in `keybank.csv` in clear text. A real KM (ETSI GS QKD 014)
  keeps keys in hardware and the client would authenticate with mutual TLS. Not addressed here.
- A malicious KM returning the same material under two ids would break OTP. Trust in the KM is a
  premise of QKD; detection would need key fingerprints in the envelope (future scope).

**Conclusion.** One-time use holds for every level: a key id is issued once, used for exactly one
message, each byte of pad is used once, and failed sends burn the key. Verified by 14 unit tests
and 2 integration tests against the real simulator.
