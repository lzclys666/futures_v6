#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青与布伦特原油价差.py
因子: BU_BU_SPD_BU_BRENT = 沥青与布伦特原油比价（CNY/吨 ÷ CNY/桶 = 无量纲比值）

公式: BU_BU_SPD_BU_BRENT = BU0结算价 ÷ SC0结算价
（注：Brent无免费源，用SC上海原油替代；BU是CNY/吨，SC是CNY/桶，单位不同故为无量纲比值）

当前状态: [⚠️待修复]（单位换算问题）
- L1: AKShare futures_main_sina('BU0') + futures_main_sina('SC0')，source_confidence=1.0
- L2: 无备选源（Brent无免费API，SC0替代）
- L3: save_l4_fallback() 兜底
- 问题: BU是元/吨，SC是元/桶，单位不统一，正确换算应为 BU/(SC×7.33/FX)
- 解决方案: 需接入Brent价格源（EIA API或Wind），或修正换算公式

订阅优先级: ★★★
替代付费源: EIA API Brent原油 / Wind / 普氏
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "BU_BU_SPD_BU_BRENT"
SYMBOL = "BU"
BOUNDS = (4.0, 10.0)


def fetch_bu():
    """L1: BU0沥青期货结算价"""
    print("[L1] AKShare futures_main_sina(symbol='BU0')...")
    df = ak.futures_main_sina(symbol="BU0")
    if df is None or df.empty:
        raise ValueError("BU0 empty")
    latest = df.sort_values("日期").iloc[-1]
    close = float(latest.get("动态结算价") or latest.get("收盘价") or 0)
    if close <= 0:
        raise ValueError(f"BU0结算价<=0: {close}")
    return close


def fetch_sc():
    """L1: SC0上海原油期货结算价（替代Brent）"""
    print("[L1] AKShare futures_main_sina(symbol='SC0')...")
    df = ak.futures_main_sina(symbol="SC0")
    if df is None or df.empty:
        raise ValueError("SC0 empty")
    latest = df.sort_values("日期").iloc[-1]
    close = float(latest.get("动态结算价") or latest.get("收盘价") or 0)
    if close <= 0:
        raise ValueError(f"SC0结算价<=0: {close}")
    return close


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    raw_value = None

    # L1: BU0 + SC0
    try:
        bu = fetch_bu()
        sc = fetch_sc()
        raw_value = round(bu / sc, 4)
        print(f"[L1] BU={bu} SC={sc} ratio={raw_value}")
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源（Brent无免费API，SC0替代）
    if raw_value is None:
        print("[L2] 无备选源（Brent无免费API，SC0已是最佳替代）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青与布伦特价差)"):
            pass
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青与布伦特价差)"):
            pass
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source="akshare_futures_main_sina(SC替代Brent)", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} (BU={bu}/SC={sc})")
