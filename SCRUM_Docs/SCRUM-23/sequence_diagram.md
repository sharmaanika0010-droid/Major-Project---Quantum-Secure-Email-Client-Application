Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
Ticket: SCRUM-23

# QuMail - Sequence Diagram: Level 2 (Quantum-aided AES) send and receive

```mermaid
sequenceDiagram
    actor Alice as Sender (Alice)
    participant UI as Streamlit UI
    participant L2 as level2.py
    participant KM as Key Manager (KM simulator)
    participant AES as aes.py (HKDF + AES-256-GCM)
    participant GM as GmailAdapter
    participant Mail as Gmail
    participant UI2 as Streamlit UI (Receiver)
    actor Bob as Receiver (Bob)

    Note over Alice,Mail: SEND (Level 2)
    Alice->>UI: Compose, select Level 2, click Send
    UI->>L2: send_level2(to, subject, body, attachments)
    L2->>KM: POST /keys/request {key_bytes: 32}
    KM-->>L2: key_id (RESERVED) + key material
    L2->>AES: encrypt(body, material, key_id)
    AES-->>L2: QuMail envelope (Key-ID, Nonce, ciphertext+tag)
    L2->>AES: encrypt(each attachment) -> name.qumail
    L2->>GM: send_message(to, subject, envelope, files)
    GM->>Mail: Gmail API send (ciphertext only)
    Mail-->>GM: message id
    L2-->>UI: message id, key_id
    UI-->>Alice: Sent encrypted

    Note over Mail,Bob: RECEIVE (Level 2)
    Bob->>UI2: Fetch inbox
    UI2->>GM: list_messages()
    GM->>Mail: Gmail API list/get
    Mail-->>UI2: messages (envelope detected, lock icon)
    Bob->>UI2: Click Decrypt
    UI2->>L2: read_level2(message)
    L2->>AES: parse_envelope -> Key-ID
    L2->>KM: GET /keys/{key_id}
    KM-->>L2: key material (410 if already consumed)
    L2->>AES: decrypt(envelope, material)
    AES-->>L2: plaintext (or authentication failure)
    L2->>KM: POST /keys/consume {key_ids}
    KM-->>L2: consumed
    L2-->>UI2: body + decrypted attachments
    UI2-->>Bob: Show message
```

## Failure paths (fail closed)
- KM down or key bank empty at send: nothing is sent, error shown.
- Wrong key, modified ciphertext or swapped Key-ID at receive: GCM authentication fails, key is not consumed.
- Key already consumed: KM returns 410, message cannot be decrypted again.

## Source of design
- From project documents: Level 2 = QKD key seeds AES (HKDF-SHA256 -> AES-256-GCM), only Key-ID in the email, QUMAIL-V1 envelope, KM endpoints (/keys/request, /keys/{id}, /keys/consume), RESERVED -> CONSUMED states, fail closed.
- My assumptions: receiver (not sender) consumes the key after a successful decrypt, one 1 KB key block per message, attachments saved as `<name>.qumail`.
