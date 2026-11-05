@echo off
REM QuMail - full regression run (SCRUM-68). Run from the project root:  scripts\run_regression.bat
REM Writes everything to reports\regression_<date>.txt so the numbers can be pasted into the report.
setlocal
if not exist reports mkdir reports
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set TODAY=%%i
set OUT=reports\regression_%TODAY%.txt
echo QuMail regression - %TODAY% %time% > %OUT%
python --version >> %OUT% 2>&1
git rev-parse --short HEAD >> %OUT% 2>&1
echo. >> %OUT%
echo === 1. Static analysis === >> %OUT%
python -m ruff check src tests >> %OUT% 2>&1
python -m bandit -c bandit.yaml -r src -q >> %OUT% 2>&1
echo. >> %OUT%
echo === 2. Unit tests (default, perf excluded) === >> %OUT%
python -m pytest -q -p no:cacheprovider >> %OUT% 2>&1
echo. >> %OUT%
echo === 3. Integration (real KM simulator) === >> %OUT%
python -m pytest -q -p no:cacheprovider -m integration >> %OUT% 2>&1
echo. >> %OUT%
echo === 4. Performance === >> %OUT%
python -m pytest -q -p no:cacheprovider -m perf >> %OUT% 2>&1
echo. >> %OUT%
echo Done. Report: %OUT%
type %OUT%
endlocal
