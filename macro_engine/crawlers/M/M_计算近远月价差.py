#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_计算近远月价差.py
因子: M_SPD_NEAR_FEAR = 豆粕近远月价差

公式: M_SPD_NEAR_FEAR = M0主力收盘价 - M2次主力收盘价（元/吨）

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol="M0"/"M2") — 新浪期货主力/次主力合约
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
FACTOR_CODE = "M_SPD_NEAR_FEAR"
BOUNDS = (-500, 500)


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1: M0 - M2
    try:
        df0 = ak.futures_main_sina(symbol="M0")
        df2 = ak.futures_main_sina(symbol="M2")
        if df0 is not None and len(df0) >= 1 and df2 is not None and len(df2) >= 1:
            close_col = [c for c in df0.columns if '收盘' in str(c) or '最新' in str(c)]
            if close_col:
                main_close = float(df0.iloc[-1][close_col[0]])
                far_close = float(df2.iloc[-1][close_col[0]])
                spread = round(main_close - far_close, 2)
                if BOUNDS[0] <= spread <= BOUNDS[1]:
                    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, spread,
                               source_confidence=1.0, source="akshare_futures_main_sina")
                    print(f"[OK] {FACTOR_CODE}={spread} obs={obs_date}")
                    return
                else:
                    print(f"[WARN] {FACTOR_CODE}={spread} out of {BOUNDS}")
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")

    # L4: DB回补
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
