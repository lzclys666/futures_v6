#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭期货近远月价差.py
因子: J_SPD_NEAR_FAR = 焦炭期货近远月价差

公式: J_SPD_NEAR_FAR = J0收盘价 - J1收盘价（元/吨）

当前状态: [✅正常]
- 数据源: AKShare futures_main_sina("J0") - futures_main_sina("J1")
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

SYMBOL = "J"
FACTOR_CODE = "J_SPD_NEAR_FAR"
BOUNDS = (-200, 200)

def fetch():
    df0 = ak.futures_main_sina(symbol="J0")
    df0['日期'] = pd.to_datetime(df0['日期']).dt.date
    j0 = float(df0.sort_values('日期').iloc[-1]['收盘价'])

    df1 = ak.futures_main_sina(symbol="J1")
    df1['日期'] = pd.to_datetime(df1['日期']).dt.date
    j1 = float(df1.sort_values('日期').iloc[-1]['收盘价'])

    raw_value = j0 - j1
    obs_date = df0.sort_values('日期').iloc[-1]['日期']
    return raw_value, obs_date

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        raw_value, obs_date = fetch()
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source='AKShare', source_confidence=0.9)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
