#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EG_抓取_工厂库存.py
因子: EG_STK_WARRANT = 乙二醇工厂库存

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_inventory_em(symbol='乙二醇') 库存列
- L4: db_utils save_l4_fallback
"""
import sys, os, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak

FACTOR_CODE = "EG_STK_WARRANT"
SYMBOL = "EG"
BOUNDS = (3000, 500000)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1
    try:
        print("[L1] AKShare futures_inventory_em(symbol='乙二醇')...")
        df = ak.futures_inventory_em(symbol="乙二醇")
        if df is None or df.empty:
            raise ValueError("Empty DataFrame")
        df = df.dropna(subset=['库存'])
        if df.empty:
            raise ValueError("库存列全为空")
        latest = df.iloc[-1]
        obs = datetime.datetime.strptime(str(latest['日期'])[:10], '%Y-%m-%d').date()
        raw_value = float(latest['库存'])

        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return

        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs, raw_value, source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="乙二醇工厂库存")

if __name__ == "__main__":
    run()
