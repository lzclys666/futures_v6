@echo off
cd /d D:\futures_v6\macro_engine\scripts
python factor_collector_main.py --mode %1
python compute_ic_heatmap.py || exit /b 0