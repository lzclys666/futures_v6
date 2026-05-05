#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EG_计算_期现基差.py
因子: EG_SPD_BASIS = 乙二醇期现基差

公式: 现货价格 - 期货主力合约价格

当前状态: [✅正常]
- L1: AKShare futures_spot_price_daily(vars_list=['EG']) dom_basis
- L4: db_utils save_l4_fallback

数据源: AKShare免费接口，无需付费订阅
"""
import sys, os, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak

FACTOR_CODE = "EG_SPD_BASIS"
SYMBOL = "EG"
BOUNDS = (-2000, 2000)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1: AKShare futures_spot_price_daily
    try:
        print("[L1] AKShare futures_spot_price_daily(vars_list=['EG'])...")
        # Use a date range to get recent data
        end_day = obs_date.strftime('%Y%m%d')
        start_day = (obs_date - datetime.timedelta(days=10)).strftime('%Y%m%d')
        df = ak.futures_spot_price_daily(start_day=start_day, end_day=end_day, vars_list=["EG"])
        if df is None or df.empty:
            raise ValueError("Empty DataFrame")
        df = df.dropna(subset=['dom_basis'])
        if df.empty:
            raise ValueError("dom_basis列全为空")
        latest = df.iloc[-1]
        obs = datetime.datetime.strptime(str(latest['date'])[:8], '%Y%m%d').date()
        raw_value = float(latest['dom_basis'])

        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return

        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs, raw_value, source_confidence=1.0, source='akshare_futures_spot_price_daily')
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="乙二醇期现基差")

if __name__ == "__main__":
    run()
