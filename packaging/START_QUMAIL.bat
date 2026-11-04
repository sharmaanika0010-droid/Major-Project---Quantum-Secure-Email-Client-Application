@echo off
REM Starts the Key Manager simulator in its own window, then the QuMail client.
cd /d "%~dp0"
start "QuMail Key Manager (port 5000)" "%~dp0QuMail-KM\QuMail-KM.exe"
timeout /t 2 >nul
start "" "%~dp0QuMail\QuMail.exe"
