@echo off
REM 因子数据采集系统 - 部署检查脚本
REM 运行：run_deployment_check.bat

echo ========================================================
echo 因子数据采集系统 - 部署检查
echo ========================================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装或未添加到 PATH
    echo 请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 运行部署检查
python deployment_check.py

echo.
echo ========================================================
echo 部署检查完成
echo ========================================================
echo.
echo 如果所有检查都通过，系统已准备就绪。
echo 否则请按照建议修复问题。
echo.
pause