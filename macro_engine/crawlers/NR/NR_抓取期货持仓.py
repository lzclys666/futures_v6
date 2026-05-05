#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NR_抓取期货持仓.py
因子: NR_FUT_OI = 20号胶期货主力合约持仓量

公式: NR_FUT_OI = NR0主力合约日持仓量（手）

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol="NR0") — 新浪期货主力合约日K线
- L2: 无备源
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak

FACTOR_CODE = "NR_FUT_OI"
SYMBOL = "NR"
BOUNDS = (10000, 200000)


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    value = None

    try:
        df = ak.futures_main_sina(symbol='NR0')
        if df is not None and not df.empty:
            latest = df.sort_values('日期').iloc[-1]
            oi = float(latest['持仓量'])
            if BOUNDS[0] <= oi <= BOUNDS[1]:
                value = oi
                print(f"[L1] NR持仓量={oi:.0f}手")
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")

    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source_confidence=1.0, source='akshare_futures_main_sina')
        print(f"[OK] {FACTOR_CODE}={value:.0f} obs={obs_date}")
    else:
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
