@echo off
setlocal
cd /d "%~dp0"
echo This registers a DAILY 08:30 task in your Windows COMPUTER local timezone.
echo Your PC needs to be powered on and allowed to run scheduled tasks.
echo No changes to ChatGPT or cloud automations are made.
pause
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL_DAILY_REFRESH_0830.ps1"
if errorlevel 1 echo Scheduling failed. Review Windows permissions / Task Scheduler.
pause
