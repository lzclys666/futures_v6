@echo off
REM 因子数据采集系统 - 快速演示脚本
REM 运行：run_demo.bat

echo ========================================================
echo 因子数据采集系统 - 快速演示
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

REM 检查 AKShare 包
python -c "import akshare" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  AKShare 包未安装，正在尝试安装...
    pip install akshare -q
    if errorlevel 1 (
        echo ❌ AKShare 安装失败
        echo 请手动运行: pip install akshare
        pause
        exit /b 1
    )
    echo ✅ AKShare 安装成功
)

REM 运行演示
python demo_quick_test.py

echo.
echo ========================================================
echo 演示完成
echo ========================================================
echo.
echo 结果已保存到 demo_output/ 目录
echo 查看日志: demo_logs/
echo.
pause