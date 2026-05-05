#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭期货仓单.py
因子: J_STK_WARRANT = 焦炭期货仓单

公式: J_STK_WARRANT = 仓单数量（手）

当前状态: [✅正常]
- 数据源: AKShare futures_warehouse_receipt_dce(date, symbol='焦炭')
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

SYMBOL = "J"
FACTOR_CODE = "J_STK_WARRANT"
BOUNDS = (0, 50000)

def fetch():
    pub_date, obs_date = get_pit_dates()
    from datetime import timedelta
    for days_back in range(7):
        d = obs_date - timedelta(days=days_back)
        try:
            df = ak.futures_warehouse_receipt_dce(date=d.strftime("%Y%m%d"))
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    row_str = ' '.join(str(v) for v in row.values)
                    if '焦炭' in row_str or row_str.strip().startswith('J'):
                        for val in row.values:
                            if isinstance(val, (int, float)) and not pd.isna(val) and val > 0:
                                return float(val), d
        except Exception as e:
            continue
    raise ValueError("DCE焦炭仓单7天回溯全部失败")

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        raw_value, obs_date = fetch()
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source='AKShare', source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
