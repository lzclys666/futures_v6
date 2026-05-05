#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP_聚丙烯期货持仓量.py
因子: PP_FUT_OI = 聚丙烯期货主力合约持仓量
当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol="PP0")
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

FCODE = "PP_FUT_OI"
SYM = "PP"
BOUNDS = (100000, 800000)


def fetch():
    df = ak.futures_main_sina(symbol="PP0")
    if df.empty:
        raise ValueError("no data")
    latest = df.sort_values('日期').iloc[-1]
    return float(latest['持仓量']), pd.to_datetime(latest['日期']).date()


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
    save_to_db(FCODE, SYM, pub_date, obs_date, raw_value, source_confidence=1.0, source='AKShare_Sina_PP0')
    print(f"[OK] {FCODE}={raw_value} obs={obs_date}")


if __name__ == "__main__":
    main()
