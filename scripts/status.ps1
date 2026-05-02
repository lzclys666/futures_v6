# 状态检查脚本
# 期货智能交易系统 V6.0

Write-Host "[Status] 系统状态检查" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# 检查进程
$pythonRunning = Get-Process python -ErrorAction SilentlyContinue
$nodeRunning = Get-Process node -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "进程状态:" -ForegroundColor Yellow
if ($pythonRunning) {
    Write-Host "  Python: 运行中 (PID: $($pythonRunning.Id)" -ForegroundColor Green
} else {
    Write-Host "  Python: 未运行" -ForegroundColor Red
}

if ($nodeRunning) {
    Write-Host "  Node:   运行中 (PID: $($nodeRunning.Id)" -ForegroundColor Green
} else {
    Write-Host "  Node:   未运行" -ForegroundColor Red
}

# 检查端口
Write-Host ""
Write-Host "端口状态:" -ForegroundColor Yellow
$ports = @(8000, 5173, 30001, 30011)
foreach ($port in $ports) {
    $connection = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue
    if ($connection.TcpTestSucceeded) {
        Write-Host "  Port $port : 开放" -ForegroundColor Green
    } else {
        Write-Host "  Port $port : 关闭" -ForegroundColor Red
    }
}

# 检查文件
Write-Host ""
Write-Host "文件状态:" -ForegroundColor Yellow
$files = @(
    "D:\futures_v6\run.py",
    "D:\futures_v6\api\macro_api_server.py",
    "D:\futures_v6\macro_engine\output\AU_macro_daily_20260424.csv"
)
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  $(Split-Path $file -Leaf): 存在" -ForegroundColor Green
    } else {
        Write-Host "  $(Split-Path $file -Leaf): 缺失" -ForegroundColor Red
    }
}

# 检查今日信号
Write-Host ""
Write-Host "今日信号:" -ForegroundColor Yellow
$today = Get-Date -Format "yyyyMMdd"
$signalFiles = Get-ChildItem "D:\futures_v6\macro_engine\output\*_macro_daily_$today.csv" -ErrorAction SilentlyContinue
if ($signalFiles) {
    foreach ($file in $signalFiles) {
        $symbol = $file.Name.Split('_')[0]
        Write-Host "  $symbol : 已生成" -ForegroundColor Green
    }
} else {
    Write-Host "  今日信号尚未生成" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
