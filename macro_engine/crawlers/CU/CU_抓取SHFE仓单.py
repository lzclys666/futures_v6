#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CU_抓取_SHFE仓单.py
因子: CU_WRT_SHFE = SHFE铜仓单

公式: 数据采集（从SHFE仓单dict中提取铜-完税商品总计）

当前状态: [✅正常]
- L1: AKShare futures_shfe_warehouse_receipt(date=YYYYMMDD) 返回dict
- L4: db_utils save_l4_fallback

已知限制: SHFE API返回dict格式，需解析铜键
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak
from datetime import date, timedelta

FACTOR_CODE = "CU_WRT_SHFE"
SYMBOL = "CU"
BOUNDS = (5000, 200000)

def try_date(d):
    if d.weekday() >= 5:
        return None
    date_str = d.strftime('%Y%m%d')
    try:
        r = ak.futures_shfe_warehouse_receipt(date=date_str)
        if isinstance(r, dict) and r and '铜' in r:
            return d, r
    except Exception:
        pass
    return None

def get_last_trading_day_with_data():
    today = date.today()
    for days in range(80):
        d = today - timedelta(days=days)
        result = try_date(d)
        if result is not None:
            return result
    return None, None

def get_wrt_from_cu_df(cu_df):
    rows = cu_df[cu_df['WHABBRNAME'].str.contains('完税商品总计', na=False)]
    if not rows.empty:
        for _, row in rows.iterrows():
            v = float(row['WRTWGHTS'])
            if v > 0:
                return v
    rows = cu_df[cu_df['WHABBRNAME'].str.contains('总计', na=False)]
    if not rows.empty:
        for _, row in rows.iterrows():
            v = float(row['WRTWGHTS'])
            if v > 0:
                return v
    valid = cu_df[cu_df['WHABBRNAME'].notna() & (cu_df['WHABBRNAME'] != '')]
    return float(valid['WRTWGHTS'].sum())

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1
    try:
        print("[L1] AKShare futures_shfe_warehouse_receipt()...")
        result = get_last_trading_day_with_data()
        obs, r = result[0], result[1]
        if obs is None or r is None:
            raise ValueError("无法获取SHFE仓单日期")
        cu_df = r.get('铜', None)
        if cu_df is None:
            raise ValueError("铜不在仓单数据中")
        raw_value = get_wrt_from_cu_df(cu_df)

        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return

        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs, raw_value, source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="SHFE铜仓单")

if __name__ == "__main__":
    run()
