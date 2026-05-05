#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭期货近远月价差.py
因子: J_SPD_NEAR_FAR = 焦炭期货近远月价差

公式: J_SPD_NEAR_FAR = J0收盘价 - J1收盘价（元/吨）

当前状态: [⚠️待修复]
- J1（焦炭次月合约）在新浪无数据，futures_main_sina("J1")返回空
- 当前用L4回补
- 解决方案：等AKShare支持J1或改用其他数据源
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
    # J1在新浪无数据，直接跳到L4
    raise ValueError("J1(焦炭次月合约)在新浪无数据，futures_main_sina('J1')返回空")

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
