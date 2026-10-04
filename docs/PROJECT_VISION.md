# QuMail — Project Vision Document

**Project:** QuMail — Quantum Secure Email Client
**Team:** Anika Sharma (Lead / Architecture & DevOps), Amit Chouhan (Email Integration & GUI), Umang Goswami (Cryptography & Key Manager)
**Duration:** 28 Sep 2026 – 27 Oct 2026 (30 days, 6 sprints)
**Repository:** https://github.com/sharmaanika0010-droid/Major-Project---Quantum-Secure-Email-Client-Application
**Tracker:** https://qumail.atlassian.net (Project key: SCRUM)

## 1. Problem Statement

Today's email security (TLS, PGP, S/MIME) relies on mathematical hardness assumptions — RSA, ECC — which are known to be breakable by sufficiently powerful quantum computers. Organisations that handle sensitive communication (defence, space agencies, finance) need an email solution whose confidentiality does not depend on those assumptions.

Quantum Key Distribution (QKD) provides keys whose secrecy is guaranteed by physics rather than computation. However, no mainstream email client can consume QKD keys from a Key Manager (KM) and use them to protect ordinary emails sent over public providers like Gmail or Yahoo.

## 2. Vision

QuMail is a desktop email client that lets a user send and receive email through existing providers (Gmail, Yahoo) while transparently encrypting the content with quantum-distributed keys obtained from a Key Manager — offering selectable security levels from "no encryption" up to information-theoretically secure One-Time Pad.

## 3. Goals & Objectives

| # | Objective | Success measure |
|---|-----------|-----------------|
| G1 | Interface with a Key Manager over a REST API to fetch quantum keys | KM simulator running; /get_key returns fresh keys, marks them consumed |
| G2 | Support 4 security levels selectable per email | Level 1 (none), Level 2 (Quantum-aided AES), Level 3 (One-Time Pad), Level 4 (extra option) working end-to-end |
| G3 | Work with real email providers | Send + receive via Gmail and Yahoo (IMAP/SMTP) with attachments |
| G4 | Usable GUI | Login, inbox, compose, security-level selector, key-status indicator |
| G5 | Engineering quality | CI/CD (GitHub Actions: lint + tests), unit tests on crypto/KM, no hard-coded secrets |
| G6 | Complete documentation | 8 UML diagrams, README, final report, PPT, demo video |

## 4. Scope

**In scope:** KM simulator (mock QKD key bank) with REST endpoints; encryption modules for Levels 1–4; IMAP/SMTP integration with Gmail and Yahoo; desktop GUI (Windows); attachment encryption; key-usage logging; packaged Windows executable.

**Out of scope (future work):** Real QKD hardware; mobile clients; large-scale multi-user KM server; post-quantum public-key algorithms as primary mode.

## 5. High-Level Architecture

Key Manager (simulator) <--REST (get_key / key_id)--> QuMail Client [GUI -> Crypto (L1/L2 AES/L3 OTP/L4) -> Email I/O] <--IMAP/SMTP--> Gmail / Yahoo

Encrypted email carries metadata (security level, key ID, nonce) in headers so the receiver can fetch the matching key from the KM and decrypt.

## 6. Stakeholders

| Stakeholder | Interest |
|-------------|----------|
| End user (sender / receiver) | Easy, secure email without changing provider |
| Key Manager operator | Correct key consumption, no key reuse |
| Evaluators / faculty | Working demo, sound design, DevOps practices, documentation |

## 7. Team Responsibilities

| Member | Ownership |
|--------|-----------|
| Anika Sharma | Coordination, UML & architecture, CI/CD, deployment, reports |
| Amit Chouhan | IMAP/SMTP integration, GUI, attachment handling, email-flow testing |
| Umang Goswami | KM simulator, crypto Levels 1–4, security review, crypto unit tests |

## 8. Timeline (6 sprints)

| Sprint | Dates | Focus |
|--------|-------|-------|
| 1 | 28 Sep – 2 Oct | Design (UML), KM stub, login/inbox, Level 1–2 modules |
| 2 | 3 – 7 Oct | Level 3, integration of all levels, Yahoo, CI skeleton |
| 3 | 8 – 12 Oct | Unit/integration tests, bug fixing, mid-point PPT |
| 4 | 13 – 17 Oct | Hardening, .env, static analysis, packaging, regression |
| 5 | 18 – 22 Oct | Demo video, report chapters 1–6 |
| 6 | 23 – 27 Oct | Review, rehearsal, final submission & viva |

## 9. Definition of Done (per task)

- Code committed on a feature branch with Jira ID in commit message (SCRUM-xx: ...)
- Pull request reviewed by at least one teammate and merged to develop.
- CI pipeline green (lint + tests)
- Jira ticket moved to Done with a short comment / screenshot

## 10. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Gmail/Yahoo auth issues (2FA, app passwords) | Blocks email testing | Set up app passwords on Day 1; test account per provider |
| OTP key exhaustion with large attachments | Level 3 fails | Size limit for Level 3; chain multiple keys; clear error state |
| Receiver cannot locate correct key | Decryption fails | Standardise envelope: key_id + level in mail headers from Day 4 |
| Schedule slippage | Incomplete features | Every 7th day is buffer/checkpoint; swap tasks within own column |

## 11. Tools

Python 3.11 · pycryptodome · Flask (KM) · imaplib/smtplib · Tkinter/PyQt (GUI) · pytest · GitHub Actions · PyInstaller · Jira · draw.io / PlantUML (UML)