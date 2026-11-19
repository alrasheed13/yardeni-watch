@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
 set "PY=py -3"
) else (
 set "PY=python"
)
echo Optional yfinance installer for ETF data fallback.
echo Supports Python 3.15 with pandas 3.1.1+ wheels.
echo.
%PY% -m pip install --upgrade pip
%PY% -m pip install --prefer-binary --only-binary=pandas,numpy -r requirements.txt
if errorlevel 1 (
 echo.
 echo Optional installation failed. The main dashboard still runs;
 echo try the built-in historical-chart downloader or CSV import.
) else (
 echo Optional price fallback installed.
)
pause
