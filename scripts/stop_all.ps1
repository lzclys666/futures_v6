# 一键停止脚本
# 期货智能交易系统 V6.0

Write-Host "[Stop] 停止所有服务..." -ForegroundColor Red

# 停止 Python 进程 (VNpy + FastAPI)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 停止 Node 进程 (前端)
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host "[Done] 所有服务已停止" -ForegroundColor Green
