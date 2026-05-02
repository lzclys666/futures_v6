#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证 API 返回格式与前端类型定义一致"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, ic_calculator, signal_scoring

print("=" * 70)
print("API 返回格式验证")
print("=" * 70)

# 1. IC 热力图格式
print("\n【1】IC 热力图 /api/ic/heatmap")
print("-" * 50)
try:
    result = ic_calculator.compute_ic_matrix(
        symbols=['AG', 'AU', 'CU'],
        factors=['basis', 'spread'],
        lookback=60,
        hold_period=5
    )
    print(f"返回字段: {list(result.keys())}")
    print(f"factors: {result.get('factors', [])}")
    print(f"symbols: {result.get('symbols', [])}")
    print(f"icMatrix: {result.get('icMatrix', [])}")
    print(f"lookbackPeriod: {result.get('lookbackPeriod')}")
    print(f"holdPeriod: {result.get('holdPeriod')}")
    print(f"updatedAt: {result.get('updatedAt')}")
    
    # 验证与前端 ICHeatmapRow 的对应关系
    print("\n  → 前端 FactorDashboardPage 期望格式:")
    print("    interface ICHeatmapRow {")
    print("      factorName: string")
    print("      icMean: number")
    print("      icStd: number")
    print("      icir: number")
    print("      ...")
    print("    }")
    print("  → 当前 API 返回的是矩阵格式，需要前端转换或后端调整")
except Exception as e:
    print(f"[ERROR] {e}")

# 2. 单品种信号格式
print("\n【2】单品种信号 /api/signal/{symbol}")
print("-" * 50)
try:
    result = signal_scoring.compute_signal_score('AG')
    print(f"返回字段: {list(result.keys())}")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    # 验证与前端 MacroSignal 的对应关系
    print("\n  → 前端 MacroSignal 期望格式:")
    print("    interface MacroSignal {")
    print("      symbol: string")
    print("      compositeScore: number  ← 当前是 0-100，前端期望 -1~1")
    print("      direction: 'LONG'|'NEUTRAL'|'SHORT'  ← 当前缺失")
    print("      updatedAt: string")
    print("      factors: FactorDetail[]  ← 当前是 factorBreakdown")
    print("    }")
except Exception as e:
    print(f"[ERROR] {e}")

# 3. 批量信号格式
print("\n【3】批量信号 /api/signal")
print("-" * 50)
try:
    signals = signal_scoring.batch_compute_signals(['AG', 'AU', 'CU'])
    print(f"返回数量: {len(signals)}")
    if signals:
        print(f"单条字段: {list(signals[0].keys())}")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 70)
print("结论：API 返回格式需要适配前端类型定义")
print("=" * 70)
