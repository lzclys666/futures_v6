#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NI_沪镍期货库存.py
因子: NI_DCE_INV = 沪镍期货库存

公式: NI_DCE_INV = 沪镍期货库存（吨）

当前状态: [✅正常]
- L1: AKShare futures_inventory_em(symbol='ni') — 东方财富期货库存
- L2: 无备源
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "NI_DCE_INV"
SYM = "NI"
BOUNDS = (30000, 150000)


def fetch():
    df = ak.futures_inventory_em(symbol='ni')
    if df.empty:
        raise ValueError("no data")
    latest = df.sort_values(df.columns[0]).iloc[-1]
    raw_value = float(latest.iloc[1])
    obs_date = pd.to_datetime(latest.iloc[0]).date()
    return raw_value, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print(f"[L1] {FCODE}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FCODE}={raw_value} out of {BOUNDS}")
        return

    save_to_db(FCODE, SYM, pub_date, obs_date, raw_value,
               source_confidence=1.0, source='akshare_futures_inventory_em')
    print(f"[OK] {FCODE}={raw_value} obs={obs_date}")


if __name__ == "__main__":
    main()
