\# Sequence Diagram — Send Email with Quantum Key (Level 2) v1



Ticket: SCRUM-21 · Date: 05 Oct 2026



\## Participants

User, Key Manager (simulator), QuMail GUI (Compose), Crypto Module (Level 2), SMTP Client, Email Provider (SMTP server)



\## Flow

1\. User composes mail, selects Level 2, clicks Send.

2\. GUI validates inputs; plaintext = body + attachments.

3\. GUI -> KM: request\_key(level=2, 32 bytes).

4-5. KM allocates next UNUSED key, marks it CONSUMED, returns key\_material + key\_id.

&#x20;  alt \[no key]: KM returns error; GUI shows "No quantum keys available".

6-10. GUI -> Crypto: encrypt\_level2. aes\_key = HKDF-SHA256(key\_material); nonce = random 12 bytes; AES-256-GCM -> ciphertext + tag.

11\. GUI builds envelope JSON {level, key\_id, nonce, ciphertext, tag} (base64) as mail body.

12-15. GUI -> SMTP Client -> Provider over STARTTLS 587 / SSL 465 with headers X-QuMail-Level, X-QuMail-KeyID. Provider replies 250 OK.

16\. GUI -> KM: log\_key\_usage(key\_id, message\_id).

17\. GUI shows "Sent securely (Level 2)".



\## Interfaces implied (for KM / crypto / SMTP modules)

\- km.request\_key(level, length) -> (key\_material, key\_id) | raises NoKeyAvailable

\- crypto.encrypt\_level2(plaintext, key\_material) -> (ciphertext, nonce, tag)

\- smtp.send(to, subject, body, headers) -> message\_id

