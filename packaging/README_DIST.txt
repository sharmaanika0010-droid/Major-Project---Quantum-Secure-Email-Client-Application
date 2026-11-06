QuMail - Quantum Secure Email Client  (portable Windows build)
===============================================================

First time
1. Double-click Create_Desktop_Shortcut.bat  ->  a "QuMail" icon appears on the Desktop.
2. Double-click the QuMail icon (or QuMail\QuMail.exe).
   The Key Manager starts silently in the background - no console window, nothing else to run.
3. Sign in with your Gmail / Yahoo address and an APP PASSWORD
   (Google account -> Security -> 2-Step Verification -> App passwords).
4. Key Manager URL stays http://localhost:5000 (press "Test" - it should report 100 keys).

Notes
- No installation and no Python required. Windows 10/11, 64-bit.
- Closing QuMail also stops the Key Manager it started. A Key Manager you started yourself
  (QuMail-KM\QuMail-KM.exe, or one on another PC) is left running.
- Key Manager log: %USERPROFILE%\.qumail\km.log
- The key bank lives in QuMail-KM\keybank.csv next to the exe. Delete it to reset to 100 fresh keys
  (previously sent encrypted mails can then no longer be opened).
- Sender and receiver must use the SAME Key Manager. For two PCs, run QuMail-KM.exe on one PC and
  set QUMAIL_KM_URL=http://<that-pc-ip>:5000 in QuMail\.env on the other.
- Settings (optional): copy QuMail\.env.example to QuMail\.env and edit.
- Contacts and the key-usage audit log are stored in %USERPROFILE%\.qumail\
- Windows SmartScreen may warn because the exe is unsigned: "More info" -> "Run anyway".
- Antivirus mail shields (e.g. Avast) can break sending; disable them while testing.
