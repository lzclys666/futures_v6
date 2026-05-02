@echo off
REM 扩展数据源采集器测试脚本
REM 运行：run_extended_test.bat

echo ========================================================
echo 扩展数据源采集器测试
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

REM 运行扩展测试
python test_extended_collectors.py

echo.
echo ========================================================
echo 扩展测试完成
echo ========================================================
echo.
echo 注意：部分测试可能需要特定环境（Wind 终端、账户等）
echo 如果测试失败，请检查相关依赖和配置。
echo.
pause