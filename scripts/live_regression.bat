@echo off
REM QuMail - LIVE regression matrix (SCRUM-69): levels 1-4 x text/attachment through a real mailbox.
REM Run from the project root with the KM simulator running. Repeat once per provider (Gmail, Yahoo).
setlocal
if not exist reports mkdir reports
set /p QUMAIL_TEST_EMAIL=Account (e.g. qumailtest71@gmail.com): 
set /p QUMAIL_TEST_PASSWORD=App password: 
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmm"') do set STAMP=%%i
set OUT=reports\live_%QUMAIL_TEST_EMAIL%_%STAMP%.txt
echo Live regression %STAMP% account %QUMAIL_TEST_EMAIL% > %OUT%
python -m pytest tests\integration\test_live_email.py -q -m live -p no:cacheprovider -rA >> %OUT% 2>&1
set QUMAIL_TEST_PASSWORD=
type %OUT%
echo.
echo Log saved: %OUT%
endlocal
