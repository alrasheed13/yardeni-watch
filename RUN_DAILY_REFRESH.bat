@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 server.py --refresh-once >>"%~dp0daily_refresh.log" 2>&1
) else (
  python server.py --refresh-once >>"%~dp0daily_refresh.log" 2>&1
)
