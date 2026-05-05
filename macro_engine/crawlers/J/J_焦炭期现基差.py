#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭期现基差.py
因子: J_SPD_BASIS = 焦炭期现基差

公式: J_SPD_BASIS = 现货价 - 期货收盘价（元/吨）

当前状态: [✅正常]
- 数据源: AKShare futures_spot_price + futures_main_sina("J0")
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

SYMBOL = "J"
FACTOR_CODE = "J_SPD_BASIS"
BOUNDS = (-300, 300)

def fetch():
    pub_date, obs_date = get_pit_dates()

    # L1a: 现货价
    spot_price = None
    spot_date = None
    for delta in range(8):
        d = obs_date - timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        try:
            df = ak.futures_spot_price(date=d.strftime('%Y%m%d'), vars_list=['J'])
            if df is not None and not df.empty:
                row = df.iloc[-1]
                spot_price = float(row.get("near_contract_price") or row.get("spot_price") or 0)
                if spot_price > 0:
                    spot_date = d
                    break
        except:
            continue

    if spot_price is None:
        raise ValueError("J现货价获取失败")

    # L1b: 期货价
    df = ak.futures_main_sina(symbol="J0")
    df['日期'] = pd.to_datetime(df['日期']).dt.date
    latest = df.sort_values('日期').iloc[-1]
    fut_close = float(latest['收盘价'])

    raw_value = spot_price - fut_close
    return raw_value, spot_date

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        raw_value, obs_date = fetch()
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source='AKShare', source_confidence=0.9)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
