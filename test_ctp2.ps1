$job = Start-Job -ScriptBlock {
    Set-Location "D:\futures_v6"
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONLEGACYWINDOWSSTDIO = "utf-8"
    & "C:\Python311\python.exe" run.py 2>&1 | Out-File -Encoding utf8BOM "D:\futures_v6\_test_output.txt"
}
$null = Wait-Job $job -Timeout 30
$result = Get-Content "D:\futures_v6\_test_output.txt" -Encoding UTF8 | Select-Object -First 100
$job | Remove-Job -Force -ErrorAction SilentlyContinue
$result
