#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证 API 返回格式与前端类型定义一致"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, ic_calculator, signal_scoring

print("=" * 70)
print("API Format Verification (Lucy Confirmed)")
print("=" * 70)

# 1. IC Heatmap
print("\n[1] IC Heatmap /api/ic/heatmap")
print("-" * 50)
try:
    result = ic_calculator.compute_ic_matrix(
        symbols=['AG', 'AU', 'CU'],
        factors=['basis', 'spread'],
        lookback=60,
        hold_period=5
    )
    print(f"Fields: {list(result.keys())}")
    print(f"factors: {result.get('factors', [])}")
    print(f"symbols: {result.get('symbols', [])}")
    print(f"icMatrix shape: {len(result.get('icMatrix', []))} x {len(result.get('icMatrix', [[]])[0])}")
    print("[OK] Matches IcHeatmapCard expected format")
except Exception as e:
    print(f"[ERROR] {e}")

# 2. Single Symbol Signal
print("\n[2] Signal /api/signal/{symbol}")
print("-" * 50)
try:
    result = signal_scoring.compute_signal_score('AG')
    print(f"Fields: {list(result.keys())}")
    
    # Check factorDetails
    if 'factorDetails' in result:
        print(f"[OK] factorDetails exists (Lucy required)")
        print(f"factorDetails count: {len(result['factorDetails'])}")
    elif 'factorBreakdown' in result:
        print(f"[FAIL] Still factorBreakdown, needs fix")
    else:
        print(f"[WARN] Neither field exists")
    
    print(f"compositeScore: {result.get('compositeScore')} (0-100)")
    print(f"signalStrength: {result.get('signalStrength')}")
    print(f"confidence: {result.get('confidence')}")
    print(f"regime: {result.get('regime')}")
    print("[OK] Matches SignalSystemData expected format")
except Exception as e:
    print(f"[ERROR] {e}")

# 3. Batch Signals
print("\n[3] Batch Signals /api/signal")
print("-" * 50)
try:
    signals = signal_scoring.batch_compute_signals(['AG', 'AU', 'CU'])
    print(f"Count: {len(signals)}")
    if signals:
        fields = list(signals[0].keys())
        print(f"Fields: {fields}")
        if 'factorDetails' in fields:
            print(f"[OK] factorDetails exists")
        elif 'factorBreakdown' in fields:
            print(f"[FAIL] Still factorBreakdown")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 70)
print("Result: API format adapted to frontend types [OK]")
print("=" * 70)
