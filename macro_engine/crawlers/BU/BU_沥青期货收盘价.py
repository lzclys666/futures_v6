#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青期货收盘价.py
因子: BU_BU_FUT_CLOSE = 沥青期货收盘价（元/吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- 数据源: AKShare futures_main_sina(symbol='BU0')，L1权威
- 采集逻辑: 取BU0主力合约动态结算价
- obs_date: 数据实际日期（'日期'列）
- bounds: [3000, 6000]元/吨（沥青期货合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd

FACTOR_CODE = "BU_BU_FUT_CLOSE"
SYMBOL = "BU"
BOUNDS = (3000.0, 6000.0)


def fetch():
    """L1: AKShare BU0沥青期货日行情"""
    print("[L1] AKShare futures_main_sina(symbol='BU0')...")
    df = ak.futures_main_sina(symbol="BU0")
    if df is None or df.empty:
        raise ValueError("no data")
    latest = df.sort_values("日期").iloc[-1]
    # 优先动态结算价，其次收盘价
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

    try:
        raw_value, actual_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            print(f"[L4] 兜底: {val}")
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                       source="db_回补", source_confidence=0.5)
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, raw_value,
               source="akshare_futures_main_sina", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={actual_date}")
