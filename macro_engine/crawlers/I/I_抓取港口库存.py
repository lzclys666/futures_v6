#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I_抓取港口库存.py
因子: I_STK_PORT = 铁矿石港口库存

公式: I_STK_PORT = 港口库存（万吨）

当前状态: [✅正常]
- 数据源: AKShare futures_inventory_em(symbol='铁矿石')
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

SYMBOL = "I"
FACTOR_CODE = "I_STK_PORT"
BOUNDS = (5000, 20000)

def fetch():
    df = ak.futures_inventory_em(symbol="铁矿石")
    df['日期'] = pd.to_datetime(df['日期']).dt.date
    latest = df.sort_values('日期').iloc[-1]
    raw_value = float(latest['库存'])
    obs_date = latest['日期']
    return raw_value, obs_date

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
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date)

if __name__ == "__main__":
    main()
