#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_抓取期货持仓.py
因子: M_POS_NET = 豆粕期货主力合约持仓量

公式: M_POS_NET = M0主力合约日持仓量（手）

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol="M0") — 新浪期货主力合约日K线
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
FACTOR_CODE = "M_POS_NET"
BOUNDS = (0, 5000000)


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        df = ak.futures_main_sina(symbol="M0")
        if df is not None and len(df) > 0:
            col_map = {str(c).strip(): c for c in df.columns}
            if "持仓量" in col_map:
                val = float(df.iloc[-1][col_map["持仓量"]])
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                               source_confidence=1.0, source="akshare_futures_main_sina")
                    print(f"[OK] {FACTOR_CODE}={val} obs={obs_date}")
                    return
                else:
                    print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")

    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
