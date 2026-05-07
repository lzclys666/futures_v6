# install_monitor_task.ps1
# Register schtasks for futures_v6 health monitor (every 5 minutes)
# Run as Administrator

$ErrorActionPreference = "Stop"

$taskName = "FuturesMonitor"
$scriptPath = "D:\futures_v6\scripts\monitor.py"
$pythonPath = "C:\Python311\python.exe"

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "[OK] Removed existing task: $taskName"
}

# Create the action
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "$scriptPath --once" -WorkingDirectory "D:\futures_v6"

# Create the trigger (every 5 minutes, indefinitely)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)

# Create the settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -DontStopOnIdleEnd

# Register the task
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -User "NT AUTHORITY\SYSTEM" -Description "futures_v6 health monitor (every 5 min)"

Write-Host "[OK] Registered: $taskName (every 5 minutes, SYSTEM user)"

# Verify
$task = Get-ScheduledTask -TaskName $taskName
Write-Host "[VERIFY] State=$($task.State) Principal=$($task.Principal.UserId) LogonType=$($task.Principal.LogonType)"
