# SCRUM-19 — Compose Email Screen

## Task
Compose-email screen with To, Subject, Body and Attachment.

## Day
Day 4 — 01 October 2026

## Deliverables
- Compose Email UI
- Activity Diagram
- Attachment support
- Key Email API

## Features
- Enter recipient email
- Enter email subject
- Write email body
- Select attachment
- Send email

## API
### Send Email
POST /api/email/send

### Request
{
  "to": "user@example.com",
  "subject": "Test Email",
  "body": "Email message"
}

## Testing
- To field tested
- Subject field tested
- Body field tested
- Attachment selection tested
- Send button tested

## Activity Diagram

The activity diagram represents the complete compose-email workflow:
- Open Compose Email
- Enter recipient
- Enter subject
- Enter email body
- Add attachment
- Validate email details
- Send email
- Handle success and error cases

Diagram file:
`SCRUM-19-Activity-Diagram.drawio`

## Evidence

- Compose Email UI tested successfully.
- To, Subject and Body fields tested.
- Attachment selection tested.
- Send Email button tested.
- Activity Diagram completed.

## Git Commit
SCRUM-19: Add compose email screen