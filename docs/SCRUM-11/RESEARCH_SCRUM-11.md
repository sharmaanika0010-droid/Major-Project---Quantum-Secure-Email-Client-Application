# **SCRUM-11 – Research: QKD / Key Manager + AES / OTP libraries (28 Sep 2026)**

**Submitted by:** UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
**Ticket:** SCRUM-11



### **SCRUM-11 Details**

> Day 1 (28 Sep 2026)
> Task: Research QKD/KM concept + AES/OTP libraries (pycryptodome or similar)
> Day deliverable / checkpoint: Repo + backlog ready
> DoD: code committed with Jira ID in message, reviewed, ticket moved to Done.





### 1\. QKD \& Key Manager concept

* QKD produces shared symmetric keys between two sites over a quantum channel. **QuMail does not implement QKD**; it consumes keys.
* Each site has a Key Manager (KM/KMS). Both KMs hold matching keys identified by a **key ID**. Applications (SAE) ask their *local* KM for keys.
* Standards: ETSI GS QKD 004 (application interface: open/get key/close) and GS QKD 014 (REST/HTTPS/JSON: `enc\\\_keys`, `dec\\\_keys`, `status`).
* Sender gets `{key\\\_ID, key}`; sends only the key\_ID in the email; receiver asks own KM for the key with that ID.
* Assumption (from brief): KM bank = 100 keys x 1 KB (\~100 KB total OTP capacity).

**Our simulated KM API:** `GET /keys/status`, `POST /keys/request {bytes}`, `GET /keys/{id}` (receiver fetch), `POST /keys/consume`. States: AVAILABLE -> RESERVED -> CONSUMED. Optionally mirror ETSI 014 paths later behind the same client interface.

### 2\. Security levels

|Level|Scheme|Key use|
|-|-|-|
|1|None|0|
|2|HKDF-SHA256(QKD key, key\_id) -> AES-256-GCM|1 key block per message (reusable design choice: still mark consumed)|
|3|OTP: C = P xor K|len(P) bytes, never reused|

OTP rules: truly random, >= plaintext length, secret, single-use. Fail closed if insufficient. OTP gives no integrity -> add MAC/authenticated envelope (open item).
Capacity note: 1 KB/key means a 10 KB attachment consumes 10 keys; the 100 KB bank is exhausted quickly.

### 3\. Library comparison

|Criterion|`cryptography` (**chosen**)|`pycryptodome`|
|-|-|-|
|AES-GCM|`AESGCM` (high level, hard to misuse)|`AES.new(MODE\\\_GCM)`|
|HKDF|Built in|`Crypto.Protocol.KDF.HKDF`|
|OTP/XOR|Not provided (write 3-line XOR)|`strxor` helper|
|Windows install|Prebuilt wheels|Prebuilt wheels|
|Maintenance|Very active, PyCA|Active|
|Note|Matches project report|Fallback option|
|Decision: **`cryptography`** for AES-GCM + HKDF; `secrets`/`os.urandom` for randomness; own XOR for OTP (nothing to get wrong; do not hand-roll AES). Performance: XOR in pure Python is fine for email sizes; can use `int.from\\\_bytes` XOR or numpy if large attachments are slow.|||

### 4\. Design decisions / risks

* Nonce: 96-bit random per message, sent in envelope.
* Bind `key\\\_id` and header as GCM AAD/HKDF info to prevent envelope swapping.
* Mark keys consumed only after successful send; use RESERVED in between.
* Never log key bytes. Store KM keys outside normal message tables.
* Gmail: OAuth 2.0 via Gmail API; test accounts needed (consent-screen setup lead time).
* Open: how receiver-side KM gets matching keys in the simulation (shared bank file/DB seeded identically, two KM instances on different ports).

### 5\. Requirements

cryptography>=42.0

fastapi>=0.110

uvicorn>=0.29

streamlit>=1.33

google-api-python-client>=2.120

google-auth-oauthlib>=1.2

pytest>=8.0

