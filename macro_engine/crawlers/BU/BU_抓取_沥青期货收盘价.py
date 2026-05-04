#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青期货收盘价.py
因子: BU_FUT_CLOSE = 沥青期货收盘价（元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol='BU0')，取动态结算价，source_confidence=1.0
- L2: 无备选源（沥青期货仅有AKShare聚合，无直接免费API）
- L3: save_l4_fallback() 兜底
- bounds: [3000, 6000]元/吨（沥青期货合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "BU_FUT_CLOSE"
SYMBOL = "BU"
BOUNDS = (3000.0, 6000.0)


def fetch():
    """L1: AKShare BU0沥青期货日行情"""
    print("[L1] AKShare futures_main_sina(symbol='BU0')...")
    df = ak.futures_main_sina(symbol="BU0")
    if df is None or df.empty:
        raise ValueError("no data")
    latest = df.sort_values("日期").iloc[-1]
    close = float(latest.get("动态结算价") or latest.get("收盘价") or 0)
    if close <= 0:
        raise ValueError(f"结算价异常: {close}")
    obs_date = pd.to_datetime(latest["日期"]).date()
    return close, obs_date


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

    raw_value, actual_date = None, None

    # L1
    try:
        raw_value, actual_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源
    if raw_value is None:
        print("[L2] 无备选源（沥青期货仅有AKShare聚合，无直接免费API）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青期货收盘价)"):
            pass
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青期货收盘价)"):
            pass
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, raw_value,
               source="akshare_futures_main_sina", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={actual_date}")
