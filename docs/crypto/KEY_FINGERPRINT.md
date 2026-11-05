# Key fingerprint in the envelope (SCRUM-67)

**Problem (bug bash BB-07).** When the receiver's Key Manager is not the one the sender used
(e.g. exe KM vs. source KM, or a reset `keybank.csv`), `GET /keys/<id>` succeeds but returns
*different* key material under the same id. Decryption then fails with "Integrity check failed",
which looks like tampering and gives the user no clue what to do.

**Fix.** Every encrypted envelope (Levels 2, 3, 4) now carries

```json
"key_fp": "9f2a1c0b7d4e"          // SHA-256(key_material)[:12]
"att_fp": "..."                   // hybrid Level 3 only – fingerprint of the attachment key
```

On receive, right after fetching the key, the fingerprint is compared **before** any decryption:

| Situation | Before | Now |
|---|---|---|
| same KM, untouched mail | decrypts | decrypts (fingerprint matches) |
| different KM / key bank | "Integrity check failed" | `KeyMismatch`: "Key QK0012 from this Key Manager is not the key the sender used. Sender and receiver are not using the same Key Manager… run one KM for both sides" |
| key id unknown at KM (404) | "unknown key id" | "Key QK0012 does not exist in this Key Manager (http://…:5000) — the mail was encrypted with a different Key Manager / key bank" |
| mail tampered, same KM | "Integrity check failed" | unchanged (fingerprint matches, MAC/GCM fails) |
| old mail without `key_fp` | "Integrity check failed" | same error + "Most likely cause: …same Key Manager…" hint |

**Security note.** 12 hex characters (48 bits) of a SHA-256 hash of a 1 KB random key reveal nothing
usable about the key (pre-image resistance; 2^8192 key space). It is a public identifier, like a
certificate fingerprint. It is *not* a MAC and does not replace the HMAC/GCM tag.

**Audit.** A mismatch writes `key_mismatch` (key_id, expected_fp, got_fp) to the audit log.

Tests: `tests/test_wrong_km.py` (10 tests).
