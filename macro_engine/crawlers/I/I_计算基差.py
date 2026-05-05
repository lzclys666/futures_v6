#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I_计算基差.py
因子: I_SPD_BASIS = 铁矿石期现基差

公式: I_SPD_BASIS = 现货价 - 期货价（元/吨）

当前状态: [✅正常]
- 数据源: AKShare futures_spot_price(date, vars_list=['I'])
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
from datetime import date, timedelta

SYMBOL = "I"
FACTOR_CODE = "I_SPD_BASIS"
BOUNDS = (-200, 200)

def get_last_trading_day():
    today = date.today()
    for days_back in range(7):
        d = today - timedelta(days=days_back)
        if d.weekday() < 5:
            return d
    return today

def fetch():
    obs_date = get_last_trading_day()
    date_str = obs_date.strftime('%Y%m%d')
    df = ak.futures_spot_price(date=date_str, vars_list=['I'])
    if df.empty:
        raise ValueError(f"I现货价返回空 date={date_str}")
    row = df.iloc[0]
    raw_value = float(row['near_basis'])
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
