cd D:\futures_v6
$ErrorActionPreference = "Continue"
$job = Start-Job -ScriptBlock {
    Set-Location "D:\futures_v6"
    & "C:\Python311\python.exe" run.py 2>&1
}
$null = Wait-Job $job -Timeout 30
$result = Receive-Job $job | Select-Object -First 100
$job | Remove-Job -Force -ErrorAction SilentlyContinue
$result
