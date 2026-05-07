# futures_v6 - Start All Script
# Usage:
#   .\start-all.ps1              # Normal mode (direct start)
#   .\start-all.ps1 -Guardian    # Guardian mode (auto-restart on crash)

param([switch]$Guardian)

$ErrorActionPreference = "Continue"
$PROJECT_ROOT = "D:\futures_v6"
$BACKEND_PORT = 8000
$FRONTEND_PORT = 5173

# Ensure QClaw bin in PATH
$qclawBin = "D:\Program Files\QClaw\resources\openclaw\config\bin"
$env:PATH = "$qclawBin;$env:PATH"
Write-Host "[ENV] PATH updated, npm=$(Get-Command npm -ErrorAction SilentlyContinue)" -ForegroundColor Gray

function Test-Port([int]$Port) {
    $result = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    return ($null -ne $result)
}

if ($Guardian) {
    # Guardian mode: start API with auto-restart
    Write-Host "[GUARDIAN] Starting API service with auto-restart..." -ForegroundColor Cyan
    python "$PROJECT_ROOT\scripts\service_guardian.py" --port $BACKEND_PORT --max-restarts 10 --check-interval 30
} else {
    # Normal mode: direct start
    # Start backend
    if (Test-Port $BACKEND_PORT) {
        Write-Host "[SKIP] Backend port $BACKEND_PORT is in use" -ForegroundColor Yellow
    } else {
        Write-Host "[START] Backend..." -ForegroundColor Cyan
        Start-Process -FilePath cmd -ArgumentList "/c cd /d $PROJECT_ROOT && python -m uvicorn api.macro_api_server:app --reload --port $BACKEND_PORT" -WindowStyle Normal
        Start-Sleep -Seconds 3
        if (Test-Port $BACKEND_PORT) {
            Write-Host "[OK] Backend started" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] Backend not responding" -ForegroundColor Red
        }
    }

    # Start frontend
    if (Test-Port $FRONTEND_PORT) {
        Write-Host "[SKIP] Frontend port $FRONTEND_PORT is in use" -ForegroundColor Yellow
    } else {
        Write-Host "[START] Frontend..." -ForegroundColor Cyan
        Start-Process -FilePath cmd -ArgumentList "/c cd /d $PROJECT_ROOT\frontend\futures_trading\frontend && npm run dev" -WindowStyle Normal
        Start-Sleep -Seconds 6
        if (Test-Port $FRONTEND_PORT) {
            Write-Host "[OK] Frontend started" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] Frontend not responding, check npm window for errors" -ForegroundColor Red
        }
    }

    # Open browser
    Write-Host "[BROWSER] Opening..." -ForegroundColor Cyan
    Start-Process "http://localhost:$FRONTEND_PORT"

    Write-Host ""
    Write-Host "Backend: http://127.0.0.1:$BACKEND_PORT" -ForegroundColor White
    Write-Host "Frontend: http://localhost:$FRONTEND_PORT" -ForegroundColor White
    Write-Host ""
    Write-Host "Tip: Use -Guardian flag for auto-restart mode" -ForegroundColor Gray
    Write-Host "  .\start-all.ps1 -Guardian" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
