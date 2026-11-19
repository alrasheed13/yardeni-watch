@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
 set "PY=py -3"
) else (
 set "PY=python"
)
echo ====================================================
echo Yardeni Watch v10.2 - Windows and Python 3.15 fix
echo ====================================================
echo.
%PY% -c "import sys; print('Using Python:', sys.version.split()[0])"
if errorlevel 1 (
 echo ERROR: Python not found. Install Python 3.11+ and retry.
 pause
 exit /b 1
)
echo.
echo Launching local dashboard. No package install is required.
echo ETF auto-download is best effort. CSV import always remains available.
echo.
%PY% server.py
if errorlevel 1 echo ERROR: Dashboard failed. Please copy the error text.
pause
