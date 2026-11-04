@echo off
REM SCRUM-62 — build QuMail.exe and QuMail-KM.exe with PyInstaller (run from the repo root)
cd /d "%~dp0.."
python -m pip install -q -r requirements-dev.txt || goto :fail
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
python -m PyInstaller packaging\qumail.spec --noconfirm --clean || goto :fail
copy /y packaging\START_QUMAIL.bat dist\ >nul
copy /y packaging\README_DIST.txt dist\ >nul
echo.
echo  Build OK:
echo    dist\QuMail\QuMail.exe
echo    dist\QuMail-KM\QuMail-KM.exe
echo    dist\START_QUMAIL.bat   (starts both)
echo.
echo  Zip the whole dist\ folder to share it.
exit /b 0
:fail
echo BUILD FAILED
exit /b 1
