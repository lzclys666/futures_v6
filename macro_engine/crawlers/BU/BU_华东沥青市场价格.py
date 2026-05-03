#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_华东沥青市场价格.py
因子: BU_BU_SPT_EAST_CHINA = 华东沥青市场价格（元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [OK]正常
- 数据源: AKShare futures_spot_price(vars_list=['BU'])，L1权威
- 采集逻辑: BU取最近5个工作日现货价（华东/全国参考价）
- obs_date: 数据实际日期
- bounds: [3000, 6000]元/吨（沥青现货合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd
from datetime import timedelta

FACTOR_CODE = "BU_BU_SPT_EAST_CHINA"
SYMBOL = "BU"
BOUNDS = (3000.0, 6000.0)


def fetch(obs_date):
    """L1: AKShare 沥青现货价（尝试最近5个工作日）"""
    print("[L1] AKShare futures_spot_price(vars_list=['BU'])...")
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime("%Y%m%d")
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=["BU"])
            if df is None or df.empty:
                continue
            row = df.sort_values("date").iloc[-1]
            spot = float(row["spot_price"])
            if spot <= 0:
                continue
            actual_date = pd.to_datetime(row["date"]).date()
            print(f"[L1] 华东沥青={spot} (date={date_str})")
            return spot, actual_date
        except Exception as e:
            print(f"[L1] {date_str}: {e}")
    return None, None


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
        raw_value, actual_date = fetch(obs_date)
    except Exception as e:
        print(f"[L1] 失败: {e}")
        raw_value = None

    if raw_value is None:
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
               source="akshare_futures_spot_price", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={actual_date}")
