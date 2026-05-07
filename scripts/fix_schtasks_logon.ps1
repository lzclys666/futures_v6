<#
.SYNOPSIS
    Fix scheduled tasks logon type from "Interactive only" to S4U (run whether user is logged on or not).

.DESCRIPTION
    Changes all futures_v6 related scheduled tasks to use S4U logon type so they
    run even when no desktop session is active. Includes rollback capability.

.PARAMETER Rollback
    Switch to revert tasks back to Interactive only (LogonType = Interactive).

.EXAMPLE
    .\fix_schtasks_logon.ps1
    Applies S4U logon type to all futures_v6 tasks.

.EXAMPLE
    .\fix_schtasks_logon.ps1 -Rollback
    Reverts all futures_v6 tasks back to Interactive only logon type.

.NOTES
    Must be run as Administrator.
    No Chinese characters in this script to avoid GBK encoding issues.
#>

[CmdletBinding()]
param(
    [switch]$Rollback
)

# --- Config ---

$TaskNames = @(
    '\FuturesAPIHealthCheck',
    '\FuturesMacro_DailyScoring',
    '\FuturesMacro_ETL_Daily',
    '\FuturesMacro_FactorCollector',
    '\FuturesMacro_FactorCollector_OnBoot'
)

# Microsoft.TaskScheduler LogonType enum:
#   S4U              = 2  (Run whether user is logged on or not)
#   InteractiveToken = 3  (Interactive only / run only when user is logged on)
#   Password         = 1
#   ServiceAccount   = 5
#
# We want S4U = 2 for "run whether user is logged on or not"

$TargetLogonType   = 2   # S4U
$RollbackLogonType = 3   # InteractiveToken (Interactive only)
$TargetRunLevel    = 1   # Highest
$RunUser           = 'Administrator'

# --- Helpers ---

function Write-Status {
    param([string]$Msg, [string]$Level = 'INFO')
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $prefix = switch ($Level) {
        'OK'   { '[OK]   ' }
        'WARN' { '[WARN] ' }
        'FAIL' { '[FAIL] ' }
        default { '[INFO] ' }
    }
    Write-Host "$ts $prefix$Msg"
}

# --- Admin check ---

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(`
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Status 'This script must be run as Administrator. Exiting.' 'FAIL'
    exit 1
}

# --- Main logic ---

$desiredLogonType = if ($Rollback) { $RollbackLogonType } else { $TargetLogonType }
$actionWord = if ($Rollback) { 'Rolling back' } else { 'Fixing' }

Write-Status "$actionWord scheduled task logon types..."

$successCount = 0
$skipCount   = 0
$failCount   = 0

foreach ($taskName in $TaskNames) {
    $shortName = $taskName.TrimStart('\')
    Write-Status "Processing: $shortName"

    # 1. Check task exists
    try {
        $task = Get-ScheduledTask -TaskName $shortName -ErrorAction Stop
    } catch {
        Write-Status "Task '$shortName' not found. Skipping." 'WARN'
        $skipCount++
        continue
    }

    # 2. Read current logon type
    $currentLogonType = $task.Principal.LogonType
    $currentRunLevel  = $task.Principal.RunLevel

    Write-Status "  Current LogonType=$currentLogonType RunLevel=$currentRunLevel"

    if ($currentLogonType -eq $desiredLogonType) {
        Write-Status "  Already at desired LogonType=$desiredLogonType. No change needed." 'OK'
        $successCount++
        continue
    }

    # 3. Apply change via ScheduledTask cmdlets
    try {
        $task.Principal.LogonType = $desiredLogonType
        if (-not $Rollback) {
            $task.Principal.RunLevel = $TargetRunLevel
        }

        Set-ScheduledTask -InputObject $task -ErrorAction Stop
        Write-Status "  Updated LogonType=$desiredLogonType RunLevel=$($task.Principal.RunLevel)" 'OK'
        $successCount++
    } catch {
        Write-Status "  Set-ScheduledTask failed: $($_.Exception.Message)" 'FAIL'
        Write-Status "  Trying fallback: schtasks /change ..." 'WARN'

        # Fallback: use schtasks.exe
        try {
            if ($Rollback) {
                # schtasks /change cannot set Interactive only directly,
                # but we can use /RU with the current user
                $result = schtasks /change /TN $taskName /RU $RunUser /IT /RL LIMITED 2>&1
            } else {
                # /RU Administrator /RP "" attempts S4U-like behavior
                $result = schtasks /change /TN $taskName /RU $RunUser /RP "" /RL HIGHEST 2>&1
            }

            if ($LASTEXITCODE -eq 0) {
                Write-Status "  Fallback schtasks succeeded." 'OK'
                $successCount++
            } else {
                Write-Status "  Fallback schtasks also failed: $result" 'FAIL'
                $failCount++
            }
        } catch {
            Write-Status "  Fallback schtasks exception: $($_.Exception.Message)" 'FAIL'
            $failCount++
        }
    }
}

# --- Summary ---

Write-Host ''
Write-Status ('=' * 50)
Write-Status "$actionWord complete: $successCount OK, $skipCount skipped, $failCount failed"

if ($failCount -gt 0) {
    Write-Status 'Some tasks failed. Check error messages above.' 'WARN'
    exit 2
}

# --- Verification ---

Write-Host ''
Write-Status '--- Verification ---'

$allGood = $true

foreach ($taskName in $TaskNames) {
    $shortName = $taskName.TrimStart('\')

    try {
        $task = Get-ScheduledTask -TaskName $shortName -ErrorAction Stop
    } catch {
        Write-Status "Verify: '$shortName' not found." 'WARN'
        continue
    }

    $logonType   = $task.Principal.LogonType
    $logonLabel  = switch ($logonType) {
        2 { 'S4U (Run whether user is logged on or not)' }
        3 { 'Interactive only' }
        1 { 'Password' }
        5 { 'ServiceAccount' }
        default { "Unknown($logonType)" }
    }

    $expectedType = if ($Rollback) { $RollbackLogonType } else { $TargetLogonType }

    if ($logonType -eq $expectedType) {
        Write-Status "Verify: $shortName -> $logonLabel" 'OK'
    } else {
        Write-Status "Verify: $shortName -> $logonLabel (expected $expectedType)" 'FAIL'
        $allGood = $false
    }
}

Write-Host ''

if ($allGood) {
    Write-Status 'All tasks verified successfully.' 'OK'
    exit 0
} else {
    Write-Status 'Verification found issues. Check output above.' 'FAIL'
    exit 3
}
