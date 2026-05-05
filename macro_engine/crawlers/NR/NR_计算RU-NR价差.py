#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NR_计算RU-NR价差.py
因子: NR_SPD_RU_NR = 天然橡胶/20号胶比价

公式: NR_SPD_RU_NR = NR0主力收盘价 / RU0主力收盘价

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol="NR0"/"RU0") — 新浪期货主力合约
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

FACTOR_CODE = "NR_SPD_RU_NR"
SYMBOL = "NR"
BOUNDS = (0.5, 1.5)


def fetch():
    nr_df = ak.futures_main_sina(symbol="NR0")
    ru_df = ak.futures_main_sina(symbol="RU0")
    if nr_df.empty or ru_df.empty:
        raise ValueError("AKShare无数据")
    nr_latest = nr_df.sort_values('日期').iloc[-1]
    ru_latest = ru_df.sort_values('日期').iloc[-1]
    nr_price = float(nr_latest['收盘价'])
    ru_price = float(ru_latest['收盘价'])
    obs_date = pd.to_datetime(nr_latest['日期']).date()
    ratio = round(nr_price / ru_price, 4)
    return ratio, obs_date


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
               source_confidence=1.0, source='AKShare_Sina_NR0_RU0')
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")


if __name__ == "__main__":
    main()
