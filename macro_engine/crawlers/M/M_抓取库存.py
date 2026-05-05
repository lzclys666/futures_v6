#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_抓取库存.py
因子: M_STK_WARRANT = 豆粕仓单/库存

公式: M_STK_WARRANT = 豆粕仓单数量（手）

当前状态: [✅正常]
- L1: AKShare futures_inventory_em(symbol="豆粕") — 东方财富期货库存
- L2: 无备源
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak

SYMBOL = "M"
FACTOR_CODE = "M_STK_WARRANT"
BOUNDS = (0, 100000)


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        df = ak.futures_inventory_em(symbol="豆粕")
        if df is not None and len(df) > 0:
            val = float(df.iloc[-1].iloc[1])
            if BOUNDS[0] <= val <= BOUNDS[1]:
                save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                           source_confidence=1.0, source="akshare_futures_inventory_em")
                print(f"[OK] {FACTOR_CODE}={val} obs={obs_date}")
                return
            else:
                print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")

    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
