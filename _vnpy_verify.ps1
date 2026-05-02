$job = Start-Job -ScriptBlock {
    Set-Location "D:\futures_v6"
    $env:QT_QPA_PLATFORM = "offscreen"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONLEGACYWINDOWSSTDIO = "utf-8"
    & "C:\Python311\python.exe" run.py 2>&1 | Out-File -Encoding utf8 "D:\futures_v6\_vnpy_full_log.txt"
}
Start-Sleep 25
if (Test-Path "D:\futures_v6\_vnpy_full_log.txt") {
    $lines = Get-Content "D:\futures_v6\_vnpy_full_log.txt" -Encoding UTF8
    Write-Host "=== TOTAL LINES: $($lines.Count) ==="
    # Show key sections
    $lines | Select-Object -First 5
    Write-Host "---"
    Select-String -Path "D:\futures_v6\_vnpy_full_log.txt" -Pattern "VNpyBridge|SignalBridge|审计服务|CTP SimNow|连接成功|初始化|ERROR|FAIL|PASS" -Encoding UTF8 | Select-Object -First 20
} else { Write-Host "File not found" }
