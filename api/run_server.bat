@echo off
chcp 65001 >nul
echo ============================================
echo 期货交易系统 - API服务器进程守护
echo ============================================
echo.

set PORT=8000
set WORKDIR=D:\futures_v6\api
set LOGFILE=%WORKDIR%\server_guard.log

:restart
echo [%date% %time%] 启动服务器 (端口 %PORT%)... >> "%LOGFILE%"
cd /d "%WORKDIR%"
python -m uvicorn macro_api_server:app --host 0.0.0.0 --port %PORT% 2>> "%LOGFILE%"
echo [%date% %time%] 服务器退出，5秒后重启... >> "%LOGFILE%"
timeout /t 5 /nobreak >nul
goto restart
