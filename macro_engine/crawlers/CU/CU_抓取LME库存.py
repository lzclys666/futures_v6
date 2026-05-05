#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CU_抓取_LME库存.py
因子: CU_INV_LME = LME铜库存

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare macro_euro_lme_stock() 铜-库存列
- L4: db_utils save_l4_fallback
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak
import pandas as pd

FACTOR_CODE = "CU_INV_LME"
SYMBOL = "CU"
BOUNDS = (100000, 800000)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1
    try:
        print("[L1] AKShare macro_euro_lme_stock()...")
        df = ak.macro_euro_lme_stock()
        if df is None or df.empty:
            raise ValueError("Empty DataFrame")
        df['日期'] = pd.to_datetime(df['日期']).dt.date
        latest = df.sort_values('日期').iloc[-1]
        raw_value = float(latest['铜-库存'])
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
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="LME铜库存")

if __name__ == "__main__":
    run()
