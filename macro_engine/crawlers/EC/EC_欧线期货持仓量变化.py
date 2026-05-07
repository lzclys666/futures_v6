#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EC_欧线期货持仓量变化.py
因子: EC_POS_OI = 集运指数期货主力合约持仓量
因子: EC_POS_CHANGE = 集运指数期货持仓量日变化

公式: EC_POS_CHANGE = EC_POS_OI(today) - EC_POS_OI(yesterday)

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol='EC0') 持仓量列，source_confidence=1.0
- L4: db_utils save_l4_fallback
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback, get_latest_value
import akshare as ak
import pandas as pd

SYMBOL = "EC"
FCODE_OI = "EC_POS_OI"
FCODE_CHANGE = "EC_POS_CHANGE"
BOUNDS_OI = (100, 200000)
BOUNDS_CHANGE = (-50000, 50000)


def fetch_oi():
    """L1: 从AKShare获取主力合约持仓量"""
    print("[L1] AKShare futures_main_sina(symbol='EC0')...")
    df = ak.futures_main_sina(symbol="EC0")
    if df is None or df.empty:
        raise ValueError("Empty DataFrame")
    # 按日期排序取最新
    df = df.sort_values(df.columns[0])
    latest = df.iloc[-1]
    oi_val = float(latest.iloc[6])  # 持仓量列
    return oi_val


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FCODE_OI}/{FCODE_CHANGE} === pub={pub_date} obs={obs_date}")

    # L1: 获取今日持仓量
    try:
        oi_today = fetch_oi()
    except Exception as e:
        print(f"[L1 FAIL] {e}")
        save_l4_fallback(FCODE_OI, SYMBOL, pub_date, obs_date, extra_msg="集运指数持仓量")
        save_l4_fallback(FCODE_CHANGE, SYMBOL, pub_date, obs_date, extra_msg="集运指数持仓量变化")
        return

    if not (BOUNDS_OI[0] <= oi_today <= BOUNDS_OI[1]):
        print(f"[WARN] {FCODE_OI}={oi_today} out of {BOUNDS_OI}")
        return

    # 使用PIT日期（obs_date < pub_date）
    save_to_db(FCODE_OI, SYMBOL, pub_date, obs_date, oi_today, source_confidence=1.0)
    print(f"[OK] {FCODE_OI}={oi_today} obs={obs_date}")

    # 计算持仓量变化：需要昨日的OI值
    oi_yesterday = get_latest_value(FCODE_OI, SYMBOL, before_date=str(obs_date))
    if oi_yesterday is not None:
        pos_change = oi_today - oi_yesterday
        if BOUNDS_CHANGE[0] <= pos_change <= BOUNDS_CHANGE[1]:
            save_to_db(FCODE_CHANGE, SYMBOL, pub_date, obs_date, pos_change, source_confidence=1.0)
            print(f"[OK] {FCODE_CHANGE}={pos_change} (今日{oi_today} - 昨日{oi_yesterday}) obs={obs_date}")
        else:
            print(f"[WARN] {FCODE_CHANGE}={pos_change} out of {BOUNDS_CHANGE}")
    else:
        print(f"[SKIP] {FCODE_CHANGE} 无昨日OI数据，无法计算变化量")
        save_l4_fallback(FCODE_CHANGE, SYMBOL, pub_date, obs_date, extra_msg="集运指数持仓量变化")


if __name__ == "__main__":
    main()
