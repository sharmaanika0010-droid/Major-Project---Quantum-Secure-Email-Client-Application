QuMail - Quantum Secure Email Client  (portable Windows build)
===============================================================

1. Double-click START_QUMAIL.bat
   - a console window "QuMail Key Manager (port 5000)" opens and stays open
   - the QuMail login window opens
2. Sign in with your Gmail / Yahoo address and an APP PASSWORD
   (Google account -> Security -> 2-Step Verification -> App passwords)
3. Key Manager URL: http://localhost:5000  (press "Test" - it should say 100 keys)

Notes
- No installation and no Python required. Windows 10/11, 64-bit.
- The key bank lives in QuMail-KM\keybank.csv next to the exe. Delete it to reset
  to 100 fresh keys (previously sent encrypted mails can then no longer be opened).
- Settings (optional): copy QuMail\.env.example to QuMail\.env and edit.
- Contacts and the key-usage audit log are stored in %USERPROFILE%\.qumail\
- Windows SmartScreen may warn because the exe is unsigned: "More info" -> "Run anyway".
- Antivirus mail shields (e.g. Avast) can break sending; disable them while testing.
