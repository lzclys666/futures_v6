#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 API 模块是否能正常导入和计算"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, ic_calculator, signal_scoring

print('[OK] FastAPI app imported successfully')
print(f'[OK] IC Calculator: {type(ic_calculator).__name__}')
print(f'[OK] Signal Scoring: {type(signal_scoring).__name__}')

# 测试 IC 热力图计算
try:
    result = ic_calculator.compute_ic_matrix(
        symbols=['AG', 'AU'],
        factors=['basis'],
        lookback=30,
        hold_period=5
    )
    print(f'[OK] IC heatmap computed: {len(result.get("factors", []))} factors x {len(result.get("symbols", []))} symbols')
    print(f'    icMatrix shape: {len(result.get("icMatrix", []))} rows')
except Exception as e:
    print(f'[WARN] IC heatmap test failed: {e}')

# 测试信号评分
try:
    result = signal_scoring.compute_signal_score('AG')
    print(f'[OK] Signal score for AG: compositeScore={result.get("compositeScore", "N/A")}')
    print(f'    signalStrength={result.get("signalStrength", "N/A")}, confidence={result.get("confidence", "N/A")}')
except Exception as e:
    print(f'[WARN] Signal score test failed: {e}')

print('\n[OK] API module test complete')
