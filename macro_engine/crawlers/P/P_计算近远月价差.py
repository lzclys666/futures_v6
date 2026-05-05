#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P_计算近远月价差.py
因子: P_SPD_CONTRACT = 棕榈油近远月价差（元/吨）

公式: P_SPD_CONTRACT = P0主力收盘价 - P2次主力收盘价

当前状态: [⚠️待修复]
- L1: AKShare futures_main_sina(symbol="P0"/"P2") — 新浪期货主力/次主力
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

FACTOR_CODE = "P_SPD_CONTRACT"
SYMBOL = "P"
BOUNDS = (-500, 500)


def fetch():
    df0 = ak.futures_main_sina(symbol="P0")
    df2 = ak.futures_main_sina(symbol="P2")
    if df0.empty or df2.empty:
        raise ValueError("AKShare无P数据")
    latest0 = df0.sort_values('日期').iloc[-1]
    latest2 = df2.sort_values('日期').iloc[-1]
    close0 = float(latest0['收盘价'])
    close2 = float(latest2['收盘价'])
    spread = round(close0 - close2, 2)
    obs_date = pd.to_datetime(latest0['日期']).date()
    return spread, obs_date


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
               source_confidence=1.0, source='AKShare_Sina_P0_P2')
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")


if __name__ == "__main__":
    main()
