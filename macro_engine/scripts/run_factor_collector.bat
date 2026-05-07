@echo off
cd /d D:\futures_v6\macro_engine\scripts

REM ===== Step 1: 因子采集 =====
python factor_collector_main.py --mode %1

REM ===== Step 2: IC 热力图 =====
python compute_ic_heatmap.py || exit /b 0

REM ===== Step 3: PIT 数据质量巡检 =====
REM 退出码: 0=正常, 1=警告, 2=严重问题
REM 质量检查失败不阻断流水线
python pit_quality_check.py
set QC_EXIT=%ERRORLEVEL%
if %QC_EXIT% GEQ 2 (
    echo [ALERT][%date% %time%] pit_quality_check detected SEVERE issues (exit code: %QC_EXIT%^). Check pit_quality_check log.
) else if %QC_EXIT% EQU 1 (
    echo [WARN][%date% %time%] pit_quality_check reported warnings (exit code: %QC_EXIT%^).
) else (
    echo [OK][%date% %time%] pit_quality_check passed.
)

REM ===== Step 4: 日志轮转 =====
python D:\futures_v6\scripts\log_rotation.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARN][%date% %time%] log_rotation failed (exit code: %ERRORLEVEL%^). Check log_rotation output.
)
