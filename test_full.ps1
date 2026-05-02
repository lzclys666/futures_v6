$job = Start-Job -ScriptBlock {
    Set-Location "D:\futures_v6"
    $env:QT_QPA_PLATFORM = "offscreen"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONLEGACYWINDOWSSTDIO = "utf-8"
    & "C:\Python311\python.exe" run.py 2>&1 | Out-File -Encoding utf8 "D:\futures_v6\_full_run.txt"
}
Start-Sleep 28
if (Test-Path "D:\futures_v6\_full_run.txt") {
    Get-Content "D:\futures_v6\_full_run.txt" -Encoding UTF8 | Select-Object -First 50
} else { Write-Host "File not found within timeout" }
