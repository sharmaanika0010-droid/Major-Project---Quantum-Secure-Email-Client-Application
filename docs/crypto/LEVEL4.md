# Level 4 — Double-layer encryption

**What:** the message (and every attachment) is encrypted twice with two different authenticated ciphers and two independent keys:

```
quantum key (1 KB from KM)
   ├─ HKDF("QuMail-L4-AES")    → key_A → AES-256-GCM        (inner layer)
   └─ HKDF("QuMail-L4-CHACHA") → key_C → ChaCha20-Poly1305  (outer layer)

blob = nonce_C | tag_C | ChaCha20-Poly1305( nonce_A | tag_A | AES-GCM(plaintext) )
```

**Why:** Level 2 depends on one algorithm. If AES-GCM were broken or mis-implemented, Level 2 mail would be exposed. Level 4 needs *both* ciphers to fail. This is the same idea as cascade modes in VeraCrypt (AES-Twofish-Serpent). Both layers are AEAD, so tampering is detected at either layer.

**Cost:** one quantum key per mail (same as Level 2); ~2× CPU, +28 bytes per item. No limit on message/attachment size (unlike Level 3).

**Compared with the other levels**

| | Level 2 | Level 3 | Level 4 |
|---|---|---|---|
| Cipher | AES-256-GCM | One-Time Pad + HMAC | AES-256-GCM ⊕ ChaCha20-Poly1305 |
| Key per mail | 1 KB | ≥ message size | 1 KB |
| Secrecy | computational | information-theoretic | computational, two independent assumptions |
| Large attachments | yes | no (or Hybrid) | yes |

**Where to use:** sensitive documents too large for OTP, when long-term confidentiality matters more than speed.

**Not claimed:** Level 4 is *not* post-quantum key exchange. QuMail never exchanges keys over the network — they come pre-shared from the Key Manager (QKD). Symmetric AEAD with 256-bit keys is already considered quantum-resistant (Grover halves effective strength to 128 bits).
