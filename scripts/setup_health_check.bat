@echo off
chcp 65001 >nul 2>&1
REM ============================================================
REM  API 健康检查 - Windows 计划任务配置脚本
REM  功能: 创建每5分钟运行一次的计划任务
REM  日志: D:\futures_v6\logs\health_check.log
REM ============================================================

setlocal

set TASK_NAME=FuturesAPIHealthCheck
set SCRIPT_PATH=D:\futures_v6\scripts\api_health_check.py
set LOG_DIR=D:\futures_v6\logs
set LOG_FILE=%LOG_DIR%\health_check.log
set PYTHON_PATH=python

REM 确保日志目录存在
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo ============================================================
echo  API 健康检查计划任务配置
echo ============================================================
echo.
echo  任务名称: %TASK_NAME%
echo  脚本路径: %SCRIPT_PATH%
echo  日志文件: %LOG_FILE%
echo  执行频率: 每 5 分钟
echo.

REM 检查脚本是否存在
if not exist "%SCRIPT_PATH%" (
    echo [错误] 监控脚本不存在: %SCRIPT_PATH%
    echo 请先创建 api_health_check.py
    pause
    exit /b 1
)

REM 删除已有任务（如果存在）
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [信息] 删除已有计划任务...
    schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
)

REM 创建计划任务 - 每5分钟运行一次
REM 使用 cmd /c 包装，将输出写入日志文件
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "cmd /c \"%PYTHON_PATH% \"%SCRIPT_PATH%\" >> \"%LOG_FILE%\" 2>&1\"" ^
    /SC MINUTE ^
    /MO 5 ^
    /ST 00:00 ^
    /F

if %errorlevel% equ 0 (
    echo.
    echo [成功] 计划任务已创建!
    echo.
    echo  验证命令: schtasks /Query /TN "%TASK_NAME%"
    echo  手动运行: schtasks /Run /TN "%TASK_NAME%"
    echo  删除任务: schtasks /Delete /TN "%TASK_NAME%" /F
    echo  查看日志: type "%LOG_FILE%"
    echo.
) else (
    echo.
    echo [错误] 创建计划任务失败!
    echo 请以管理员权限运行此脚本。
    echo.
)

echo ============================================================
pause
