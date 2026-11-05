\# Activity Diagram — Compose → Encrypt → Send → Receive → Decrypt (v1)



Ticket: SCRUM-18 · Author: Anika Sharma · Date: 05 Oct 2026



\## Swimlanes

Sender (QuMail client), Key Manager (KM), Email Provider (Gmail/Yahoo), Receiver (QuMail client)



\## Main flow

1\. Sender logs in, composes mail (To/Subject/Body/attachments) and selects Security Level 1-4.

2\. Level 1 -> sent as plain text (no KM call).

3\. Level 2/3/4 -> client requests a key from KM; KM allocates the next unused key, marks it CONSUMED and returns key + key\_id.

4\. If no key is available (e.g. OTP needs key >= message length) -> error "No quantum keys available"; user may retry or lower the level.

5\. Client encrypts body + attachments (L2 AES-256-GCM, L3 One-Time Pad, L4 extra option), builds an envelope (level, key\_id, nonce, base64 ciphertext) and sends via SMTP with X-QuMail-Level / X-QuMail-KeyID headers. Key usage is logged.

6\. Provider stores and delivers the message.

7\. Receiver fetches via IMAP, reads X-QuMail headers. If level > 1, requests the key by key\_id from KM, decrypts and verifies integrity, then displays plaintext. Level 1 is displayed directly.



\## Decisions

Level = 1? · Key available? · Encrypted (level > 1)?



\## Notes

KM in Week 1 is a simulator (mock key bank). One-time use of keys is enforced by KM (CONSUMED flag).

