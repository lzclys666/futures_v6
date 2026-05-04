#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_央行黄金储备.py
因子: AU_GOLD_RESERVE_CB = 中国央行黄金储备（万盎司）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare macro_china_fx_gold()，source_confidence=1.0
- L2: 无备选源（央行黄金储备仅有国家外汇管理局发布）
- L3: save_l4_fallback() 兜底
- bounds: [1000, 10000]万盎司（央行黄金储备历史区间）

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
import re
from datetime import date

FACTOR_CODE = "AU_GOLD_RESERVE_CB"
SYMBOL = "AU"
BOUNDS = (1000.0, 10000.0)


def parse_month(s):
    """'2026年03月份' -> date(2026, 3, 1)"""
    m = re.match(r'(\d{4})年(\d{2})月份', str(s))
    if m:
        return date(int(m.group(1)), int(m.group(2)), 1)
    return None


def fetch():
    """L1: AKShare 中国央行黄金储备（月度）"""
    print("[L1] AKShare macro_china_fx_gold()...")
    df = ak.macro_china_fx_gold()
    if df is None or df.empty:
        raise ValueError("no data")
    df["_date"] = df["月份"].apply(parse_month)
    df = df.dropna(subset=["_date"])
    df = df.sort_values("_date")
    latest = df.iloc[-1]
    raw_value = float(latest["黄金储备-数值"])
    obs_date = latest["_date"]
    return raw_value, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    raw_value, data_obs_date = None, None

    # L1
    try:
        raw_value, data_obs_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源（央行黄金储备仅有国家外汇管理局发布）
    if raw_value is None:
        print("[L2] 无备选源（央行黄金储备仅有国家外汇管理局发布）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(央行黄金储备)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
            print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
        return

    # bounds校验
    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(央行黄金储备)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="akshare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={data_obs_date}")


if __name__ == "__main__":
    main()
