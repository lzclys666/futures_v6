#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NR_抓取橡胶.py
因子: NR_INV_TOTAL = 20号胶期货库存

公式: NR_INV_TOTAL = INE20号胶期货库存（吨）

当前状态: [✅正常]
- L1: AKShare futures_inventory_em(symbol="nr") — 东方财富期货库存
- L2: 无备源
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FACTOR_CODE = "NR_INV_TOTAL"
SYMBOL = "NR"
BOUNDS = (10000, 100000)


def fetch():
    df = ak.futures_inventory_em(symbol="nr")
    df['date'] = pd.to_datetime(df['日期']).dt.date
    latest = df.sort_values('date').iloc[-1]
    raw_value = float(latest['库存'])
    obs_date = latest['date']
    return raw_value, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        return

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source_confidence=1.0, source='akshare_futures_inventory_em')
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")


if __name__ == "__main__":
    main()
