# install_guardian_task.ps1
# 将 service_guardian.py 注册为 Windows 计划任务（开机/登录时自动启动）
# 用法: 以管理员权限运行此脚本

$ErrorActionPreference = "Stop"

$TASK_NAME = "FuturesV6-API-Guardian"
$PYTHON = (Get-Command python -ErrorAction SilentlyContinue).Source
$GUARDIAN_SCRIPT = "D:\futures_v6\scripts\service_guardian.py"
$ARGUMENTS = "$GUARDIAN_SCRIPT --port 8000 --max-restarts 10 --check-interval 30"

if (-not $PYTHON) {
    Write-Host "[ERROR] Python not found in PATH" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $GUARDIAN_SCRIPT)) {
    Write-Host "[ERROR] Guardian script not found: $GUARDIAN_SCRIPT" -ForegroundColor Red
    exit 1
}

Write-Host "Registering scheduled task: $TASK_NAME" -ForegroundColor Cyan

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[INFO] Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
}

# Create task action
$action = New-ScheduledTaskAction -Execute $PYTHON -Argument $ARGUMENTS

# Trigger on user logon
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Settings: run on battery, don't stop on battery, start when available
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Register the task
Register-ScheduledTask `
    -TaskName $TASK_NAME `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Futures V6 API service guardian - auto restart on crash" `
    -Force

Write-Host ""
Write-Host "[OK] Scheduled task registered: $TASK_NAME" -ForegroundColor Green
Write-Host "  Trigger: At user logon" -ForegroundColor Gray
Write-Host "  Action:  $PYTHON $ARGUMENTS" -ForegroundColor Gray
Write-Host ""
Write-Host "To manage:" -ForegroundColor White
Write-Host "  Start:   Start-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor Gray
Write-Host "  Stop:    Stop-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor Gray
Write-Host "  Remove:  Unregister-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor Gray
Write-Host "  Status:  Get-ScheduledTask -TaskName '$TASK_NAME'" -ForegroundColor Gray
