#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I_铁矿螺纹比价.py
因子: I_SPD_I_RB = 铁矿石/螺纹钢期货比价

公式: I_SPD_I_RB = I0主力收盘价 / RB0主力收盘价

当前状态: ✅正常
- L1: AKShare futures_main_sina(symbol='I0'/'RB0') — 新浪期货主力收盘价
- L4: save_l4_fallback() DB历史最新值回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak

FCODE = "I_SPD_I_RB"
SYM = "I"
BOUNDS = (0.1, 0.5)  # I/RB比价合理范围


def fetch():
    """L1: futures_main_sina 计算I/RB比价"""
    df_i = ak.futures_main_sina(symbol="I0")
    df_rb = ak.futures_main_sina(symbol="RB0")
    if df_i is None or len(df_i) == 0 or df_rb is None or len(df_rb) == 0:
        return None

    close_i = float(df_i.iloc[-1]['收盘价'])
    close_rb = float(df_rb.iloc[-1]['收盘价'])
    if close_rb == 0:
        return None

    ratio = close_i / close_rb
    return ratio


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
            print(f"[WARN] {FCODE}={raw_value:.4f} out of {BOUNDS}")
            return
        save_to_db(FCODE, SYM, pub_date, obs_date, raw_value,
                   source_confidence=1.0, source='akshare_sina_I0_RB0')
        print(f"[OK] {FCODE}={raw_value:.4f} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {type(e).__name__}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
