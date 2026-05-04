#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_华东沥青市场价格.py
因子: BU_SPT_EAST_CHINA = 华东沥青市场价格（元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_spot_price(vars_list=['BU'])，source_confidence=1.0
- L2: 无备选源（沥青现货价仅有AKShare聚合，无直接免费API）
- L3: save_l4_fallback() 兜底
- bounds: [3000, 6000]元/吨（沥青现货合理区间）

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
from datetime import timedelta

FACTOR_CODE = "BU_SPT_EAST_CHINA"
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
    # L2: 无备选源
    print("[L2] 无备选源（沥青现货价仅有AKShare聚合，无直接免费API）")
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

    raw_value, actual_date = None, None

    # L1
    try:
        raw_value, actual_date = fetch(obs_date)
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(华东沥青市场价格)"):
            pass
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(华东沥青市场价格)"):
            pass
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, raw_value,
               source="akshare_futures_spot_price", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={actual_date}")
