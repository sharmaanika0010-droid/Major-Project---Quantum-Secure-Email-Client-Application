Submitted by: UMANG GOSWAMI | GitHub: @goswamiumang108 | Email: go.umang108@gmail.com
Ticket: SCRUM-17

# QuMail - Class Diagram v1 (Day 3, Level 1 baseline)

```mermaid
classDiagram
    class EmailProvider {
        <<abstract>>
        +send_message(to, subject, body, attachments) str
        +list_messages(max_results, query) List~EmailMessage~
        +get_message(message_id) EmailMessage
    }
    class GmailAdapter {
        -credentials_file: str
        -token_file: str
        -service
        +authenticate() GmailAdapter
        +build_mime(to, subject, body, attachments) MimeMessage
        +send_message(...) str
        +list_messages(...) List~EmailMessage~
        +get_message(message_id) EmailMessage
        +download_attachment(message_id, attachment_id) bytes
        +parse_message(raw) EmailMessage
    }
    class EmailMessage {
        +message_id: str
        +sender: str
        +to: str
        +subject: str
        +date: str
        +snippet: str
        +body: str
        +attachments: List~Attachment~
    }
    class Attachment {
        +filename: str
        +content_type: str
        +data: bytes
        +attachment_id: str
    }
    class StreamlitApp {
        +Inbox tab
        +Compose tab
    }
    EmailProvider <|-- GmailAdapter
    EmailMessage "1" *-- "0..*" Attachment
    GmailAdapter ..> EmailMessage : creates
    StreamlitApp --> EmailProvider : uses
```

## Source of design
- From project documents: Gmail API + OAuth 2.0, Streamlit UI, `../../src/email/gmail_adapter.py` path, adapter functions `send_message()`, `list_messages()`, `get_message()`, `parse_message()`, provider-replaceable design, Python `email` package for MIME.
- My assumptions: the `EmailProvider` abstract class name, the `EmailMessage`/`Attachment` dataclass fields, scopes `gmail.send` + `gmail.readonly`, and fetching attachments lazily via `download_attachment`.

## Not in v1 (later tickets)
Encryption module, Key Manager client, QuMail envelope, SQLite. They plug in later without changing `EmailProvider`.
