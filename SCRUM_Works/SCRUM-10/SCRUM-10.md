# SCRUM-10 — Gmail/Yahoo IMAP-SMTP + App Password/OAuth Research

## Objective

Research and document how the application will connect to Gmail and Yahoo Mail using IMAP and SMTP.

## Tasks

- Study Gmail IMAP configuration.
- Study Gmail SMTP configuration.
- Study Yahoo Mail IMAP configuration.
- Study Yahoo Mail SMTP configuration.
- Understand App Password authentication.
- Understand OAuth 2.0 authentication.
- Identify the libraries required for implementation.
- Document required ports and security settings.

## Gmail Configuration

### IMAP

- Server: `imap.gmail.com`
- Port: `993`
- Security: SSL/TLS

### SMTP

- Server: `smtp.gmail.com`
- Port: `465` (SSL) or `587` (STARTTLS)
- Security: SSL/TLS or STARTTLS

## Yahoo Configuration

### IMAP

- Server: `imap.mail.yahoo.com`
- Port: `993`
- Security: SSL/TLS

### SMTP

- Server: `smtp.mail.yahoo.com`
- Port: `465` (SSL) or `587` (STARTTLS)
- Security: SSL/TLS or STARTTLS

## Authentication

The application should support secure authentication methods:

1. OAuth 2.0
2. App Passwords where supported

Normal email passwords should not be stored directly in the application.

## Libraries to Research

- Python `imaplib` for IMAP
- Python `smtplib` for SMTP
- `email` package for email parsing
- OAuth 2.0 library/support for authentication

## Expected Outcome

A documented authentication and mail-server configuration that can be used later to implement secure Gmail/Yahoo email
sending and receiving.

## Status

Research and documentation completed.