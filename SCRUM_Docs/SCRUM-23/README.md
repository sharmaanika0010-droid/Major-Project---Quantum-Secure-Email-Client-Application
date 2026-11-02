Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
Ticket: SCRUM-23

# [Day 5] Level 2 - Quantum-aided AES: encrypt/decrypt module

QKD key block -> HKDF-SHA256 -> AES-256-GCM. Body and attachments are encrypted; only the Key-ID travels in the email.

## Contents
- `../../src/crypto/aes.py` - encrypt/decrypt, HKDF, QuMail envelope pack/parse
- `../../src/crypto/level2.py` - `KMClient`, `send_level2()`, `read_level2()`
- `../../src/crypto/__init__.py` - package marker
- `../../src/app.py` - updated: Level 1/2 selector in Compose, lock icon + Decrypt in Inbox
- `../../tests/test_aes.py`, `../../tests/test_level2.py` - 20 tests
- `sequence_diagram.md` - sequence diagram (Mermaid)

## Run
```
pip install -r requirements.txt
python src/km_simulator/km_simulator.py      # terminal 1
streamlit run src/app.py                     # terminal 2
python -m pytest tests -q                    # tests (no Gmail or KM needed)
```
In Compose pick "Level 2 - Quantum-aided AES" and send. In Inbox, 🔒 messages have a Decrypt button.

## How it works
- Send: `/keys/request` (key becomes RESERVED) -> encrypt -> send. If the KM is down or empty, nothing is sent.
- Receive: read Key-ID -> `GET /keys/{id}` -> decrypt -> `/keys/consume`. A failed decrypt does not consume the key.
- Envelope: `QUMAIL-V1` header (Security-Level, Algorithm, Key-ID, Nonce, Content-Type) + base64 payload. Header is bound as GCM AAD and the Key-ID as HKDF context.

## Limits
- Subject line is not encrypted.
- After Decrypt the key is consumed, so the same message cannot be decrypted again (the app keeps the plaintext only for the current session).
- No endpoint to release a RESERVED key if the send fails after the key request.
- Uses the shared KM bank for both sides (simulation); real two-KM setup comes later.

## Source
- From project documents: Level 2 design, HKDF + AES-256-GCM, QUMAIL-V1 envelope, KM endpoints and states, KM simulator and Gmail adapter as they exist in the repo, Jira SCRUM-23 text (sequence diagram + working send + Level 2 module).
- My assumptions: `pycryptodome` (already in requirements.txt) instead of `cryptography` from SCRUM-11, so no requirements change; 32 B requested so the KM issues one 1 KB block; receiver consumes the key; attachments stored as `<name>.qumail`; plain-text envelope as the email body.
- Tested: 20 unit tests pass; also run end to end against the real KM simulator (send, decrypt, key consumed, second decrypt gives 410). Gmail send/receive and the Streamlit screen were not run here (needs your credentials.json).

## Commit message (when you commit)
`SCRUM-23: Add Level 2 quantum-aided AES encrypt/decrypt module and send flow`
