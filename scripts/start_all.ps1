# 一键启动脚本
# 期货智能交易系统 V6.0

Write-Host "[Start] 期货智能交易系统 V6.0" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# 1. 设置环境变量
$env:QT_QPA_PLATFORM = "offscreen"
$env:PYTHONPATH = "D:\futures_v6"

# 2. 启动 VNpy
Write-Host "[1/3] 启动 VNpy..." -ForegroundColor Yellow
Start-Process python -ArgumentList "D:\futures_v6\run.py" -WindowStyle Hidden -WorkingDirectory "D:\futures_v6"
Start-Sleep -Seconds 5

# 3. 启动 FastAPI
Write-Host "[2/3] 启动 FastAPI..." -ForegroundColor Yellow
Start-Process python -ArgumentList "-m","uvicorn","api.macro_api_server:app","--host","0.0.0.0","--port","8000" -WindowStyle Hidden -WorkingDirectory "D:\futures_v6"
Start-Sleep -Seconds 3

# 4. 启动前端
Write-Host "[3/3] 启动前端..." -ForegroundColor Yellow
Start-Process npm -ArgumentList "run","dev" -WindowStyle Hidden -WorkingDirectory "D:\futures_v6\macro_engine\frontend"

Write-Host "[Done] 所有服务已启动" -ForegroundColor Green
Write-Host ""
Write-Host "服务状态:" -ForegroundColor Cyan
Write-Host "  - VNpy:    http://localhost:30001 (CTP)"
Write-Host "  - API:     http://localhost:8000"
Write-Host "  - Frontend: http://localhost:5173"
Write-Host ""
Write-Host "查看日志:" -ForegroundColor Cyan
Write-Host "  Get-Content D:\futures_v6\.vntrader\log\vt_$(Get-Date -Format 'yyyyMMdd').log -Tail 50"
