#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_美国10年期国债收益率（名义）.py
因子: AU_US_10Y_YIELD = 美国名义10年期国债收益率（%）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- 数据源: AKShare bond_zh_us_rate()，L1权威
- 采集逻辑: 取'美国国债收益率10年'列最新一行
- obs_date: 数据日期
- bounds: [0.0, 10.0]%（历史区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd

FACTOR_CODE = "AU_US_10Y_YIELD"
SYMBOL = "AU"
BOUNDS = (0.0, 10.0)


def fetch():
    """L1: AKShare 美国10年期国债收益率"""
    print("[L1] AKShare bond_zh_us_rate()...")
    df = ak.bond_zh_us_rate()
    if df is None or df.empty:
        raise ValueError("no data")
    df = df.dropna(subset=[df.columns[0]])
    df = df.sort_values(df.columns[0])
    latest = df.iloc[-1]
    col_10y = "美国国债收益率10年"
    raw_value = float(latest[col_10y])
    obs_date = pd.to_datetime(latest[df.columns[0]]).date()
    return raw_value, obs_date


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value, obs_date = fetch()
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

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source="akshare", source_confidence=0.9)
    print(f"[OK] {FACTOR_CODE}={raw_value}% obs={obs_date}")
