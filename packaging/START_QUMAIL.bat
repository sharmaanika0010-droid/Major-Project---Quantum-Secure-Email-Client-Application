@echo off
REM Optional launcher kept for compatibility. QuMail.exe now starts the Key Manager by itself;
REM double-clicking QuMail\QuMail.exe (or the Desktop shortcut) is all that is needed.
cd /d "%~dp0"
start "" "%~dp0QuMail\QuMail.exe"
