Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
Ticket: SCRUM-17

# QuMail - Level 1 (No Quantum Security) baseline

Plain Gmail send/receive with inbox fetch. No encryption or Key Manager yet.

## Contents
- `../../src/email_service/gmail_adapter.py` - `EmailProvider` interface, `GmailAdapter` (OAuth, send, inbox fetch, attachments)
- `../../src/app.py` - Streamlit UI (Inbox + Compose, Level 1 only)
- `class_diagram_v1.md` - Class diagram v1

## Setup
1. `pip install -r requirements.txt`
2. **Add `credentials.json` yourself.** It is NOT included in this submission (it is a private Google OAuth secret). The reviewer / project manager must place their own `credentials.json` in this folder, next to `../../src/app.py`.
   - To create one: Google Cloud Console, enable the Gmail API, create an OAuth client ID of type "Desktop app", download the JSON and rename it to `credentials.json`.
   - Add the Gmail account being used as a test user on the OAuth consent screen.

## Run
`streamlit run src/app.py` (a browser window opens for Google sign-in on first run; `token.json` is created locally).

## Limits
Level 1 only. AES (Level 2), OTP (Level 3) and the Key Manager come in later tickets.
