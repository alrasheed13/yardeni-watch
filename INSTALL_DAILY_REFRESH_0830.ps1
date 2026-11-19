# Optional. Run this only if you want Windows Task Scheduler to refresh data
# at 08:30 in your COMPUTER's local time, while your computer is on/logged in.
$ErrorActionPreference='Stop'
$scriptPath=Join-Path $PSScriptRoot 'RUN_DAILY_REFRESH.bat'
if (!(Test-Path $scriptPath)) { throw "RUN_DAILY_REFRESH.bat not found" }
$exe=Join-Path $env:WINDIR 'System32\cmd.exe'
$action=New-ScheduledTaskAction -Execute $exe -Argument ('/c ""'+$scriptPath+'""') -WorkingDirectory $PSScriptRoot
$trigger=New-ScheduledTaskTrigger -Daily -At '08:30'
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName 'YardeniWatchDaily0830' -Action $action -Trigger $trigger -Settings $settings -Description 'Public Yardeni RSS, US Treasury/FRED and ETF EOD refresh' -Force | Out-Null
Write-Host 'Task YardeniWatchDaily0830 has been registered. Local PC time: 08:30.'
