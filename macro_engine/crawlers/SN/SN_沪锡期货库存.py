#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SN_沪锡期货库存.py
因子: SN_DCE_INV = 沪锡期货库存
当前状�? [✅正常]
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from common.db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "SN_DCE_INV"
SYM = "SN"
BOUNDS = (1000, 50000)


def fetch():
    df = ak.futures_inventory_em(symbol='sn')
    if df.empty:
        raise ValueError("no data")
    latest = df.sort_values(df.columns[0]).iloc[-1]
    return float(latest.iloc[1]), pd.to_datetime(latest.iloc[0]).date()


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
    save_to_db(FCODE, SYM, pub_date, obs_date, raw_value, source_confidence=1.0, source='akshare_futures_inventory_em')
    print(f"[OK] {FCODE}={raw_value} obs={obs_date}")


if __name__ == "__main__":
    main()
