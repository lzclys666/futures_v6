#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P_棕榈豆油价差.py
因子: P_SPD_P_Y = 棕榈油/豆油期货价差（元/吨）

公式: P_SPD_P_Y = P0主力收盘价 - Y0主力收盘价

当前状态: ✅正常
- L1: AKShare futures_main_sina(symbol='P0'/'Y0') — 新浪期货主力收盘价
- L4: save_l4_fallback() DB历史最新值回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "P_SPD_P_Y"
SYM = "P"
BOUNDS = (-3000, 3000)  # 棕榈-豆油价差合理范围（元/吨）


def fetch():
    """L1: futures_main_sina 计算棕榈-豆油价差"""
    df_p = ak.futures_main_sina(symbol="P0")
    df_y = ak.futures_main_sina(symbol="Y0")
    if df_p is None or len(df_p) == 0 or df_y is None or len(df_y) == 0:
        return None

    close_p = float(df_p.iloc[-1]['收盘价'])
    close_y = float(df_y.iloc[-1]['收盘价'])
    spread = close_p - close_y
    return spread


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value = fetch()
        if raw_value is None:
            print(f"[L1] {FCODE}: 数据不足")
            save_l4_fallback(FCODE, SYM, pub_date, obs_date)
            return
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FCODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FCODE, SYM, pub_date, obs_date, raw_value,
                   source_confidence=1.0, source='akshare_sina_P0_Y0')
        print(f"[OK] {FCODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {type(e).__name__}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
