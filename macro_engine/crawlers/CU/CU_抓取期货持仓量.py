#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CU_抓取_期货持仓量.py
因子: CU_FUT_OI = 沪铜期货持仓量

公式: 数据采集（主力合约持仓量）

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol='cu0') 持仓量列
- L4: db_utils save_l4_fallback
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak
import pandas as pd

FACTOR_CODE = "CU_FUT_OI"
SYMBOL = "CU"
BOUNDS = (50000, 500000)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1
    try:
        print("[L1] AKShare futures_main_sina(symbol='cu0')...")
        df = ak.futures_main_sina(symbol="cu0")
        if df is None or df.empty:
            raise ValueError("Empty DataFrame")
        df['日期'] = pd.to_datetime(df['日期']).dt.date
        latest = df.sort_values('日期').iloc[-1]
        raw_value = float(latest['持仓量'])
        obs = latest['日期']

        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return

        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs, raw_value, source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="沪铜持仓量")

if __name__ == "__main__":
    run()
