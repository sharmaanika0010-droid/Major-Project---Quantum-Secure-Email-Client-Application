@echo off
REM Creates a "QuMail" shortcut on the Desktop pointing at QuMail\QuMail.exe (with icon).
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$s = $ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'QuMail.lnk'));" ^
  "$s.TargetPath = '%~dp0QuMail\QuMail.exe';" ^
  "$s.WorkingDirectory = '%~dp0QuMail';" ^
  "$s.IconLocation = '%~dp0QuMail\qumail.ico';" ^
  "$s.Description = 'QuMail - Quantum Secure Email';" ^
  "$s.Save()"
if errorlevel 1 (echo Could not create the shortcut.) else (echo Done - "QuMail" is on your Desktop.)
pause
