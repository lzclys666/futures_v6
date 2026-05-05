#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_抓取现货和基差.py
因子: M_BASIS_SPOT_FUTURES = 豆粕现货价格

公式: M_BASIS_SPOT_FUTURES = 豆粕现货价（元/吨）

当前状态: [⚠️待修复]
- L1: AKShare futures_spot_price — 接口不稳定，有时返回空
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
FACTOR_CODE = "M_BASIS_SPOT_FUTURES"
BOUNDS = (1000, 10000)


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        date_str = obs_date.strftime("%Y%m%d")
        df = ak.futures_spot_price(date=date_str, vars_list=["M"])
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            val = float(row["spot_price"])
            if BOUNDS[0] <= val <= BOUNDS[1]:
                save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                           source_confidence=1.0, source="akshare_futures_spot_price")
                print(f"[OK] {FACTOR_CODE}={val} obs={obs_date}")
                return
            else:
                print(f"[WARN] {FACTOR_CODE}={val} out of {BOUNDS}")
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")

    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
