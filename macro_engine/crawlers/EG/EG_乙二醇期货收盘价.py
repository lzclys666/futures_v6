#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EG_抓取_期货收盘价.py
因子: EG_FUT_CLOSE = 乙二醇期货收盘价

公式: 数据采集（主力合约收盘价）

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol='EG0') 收盘价列
- L4: db_utils save_l4_fallback
"""
import sys, os, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak

FACTOR_CODE = "EG_FUT_CLOSE"
SYMBOL = "EG"
BOUNDS = (3000, 8000)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1
    try:
        print("[L1] AKShare futures_main_sina(symbol='EG0')...")
        df = ak.futures_main_sina(symbol="EG0")
        if df is None or df.empty:
            raise ValueError("Empty DataFrame")
        df = df.dropna(subset=['收盘价'])
        latest = df.iloc[-1]
        obs = datetime.datetime.strptime(str(latest['日期'])[:10], '%Y-%m-%d').date()
        raw_value = float(latest['收盘价'])

        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return

        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs, raw_value, source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="乙二醇收盘价")

if __name__ == "__main__":
    run()
