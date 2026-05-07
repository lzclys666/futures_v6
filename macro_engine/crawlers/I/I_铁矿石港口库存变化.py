#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I_铁矿石港口库存变化.py
因子: I_INV_EM = 铁矿石港口库存变化量（东方财富）

公式: I_INV_EM = 当日库存 - 前日库存（吨）

当前状态: ✅正常
- L1: AKShare futures_inventory_em(symbol='铁矿石') — 东方财富铁矿石库存
- L4: save_l4_fallback() DB历史最新值回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "I_INV_EM"
SYM = "I"
BOUNDS = (-5000, 5000)  # 库存变化合理范围（万吨）


def fetch():
    """L1: futures_inventory_em 铁矿石库存变化"""
    df = ak.futures_inventory_em(symbol="铁矿石")
    if df is None or len(df) < 2:
        return None
    df['日期'] = pd.to_datetime(df['日期']).dt.date
    df = df.sort_values('日期')
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    change = float(latest['库存']) - float(prev['库存'])
    return change


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
                   source_confidence=0.9, source='akshare_inventory_em')
        print(f"[OK] {FCODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {type(e).__name__}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
