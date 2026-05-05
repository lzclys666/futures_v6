#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NI_抓取SHFE仓单.py
因子: NI_WRT_SHFE = 上期所沪镍仓单

公式: NI_WRT_SHFE = SHFE镍注册仓单重量（吨）

当前状态: [✅正常]
- L1: AKShare futures_shfe_warehouse_receipt — 上期所仓单数据
- L2: 无备源
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
from datetime import date, timedelta

FACTOR_CODE = "NI_WRT_SHFE"
SYMBOL = "NI"
BOUNDS = (5000, 80000)


def try_date(d):
    if d.weekday() >= 5:
        return None
    date_str = d.strftime('%Y%m%d')
    try:
        r = ak.futures_shfe_warehouse_receipt(date=date_str)
        if isinstance(r, dict) and r and '镍' in r:
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
    return float(cu_df[cu_df['WHABBRNAME'].notna()]['WRTWGHTS'].sum())


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        obs_date_data, r = get_last_trading_day_with_data()
        if obs_date_data is None:
            raise ValueError("无法获取SHFE镍仓单日期")
        cu_df = r.get('镍', None)
        if cu_df is None:
            raise ValueError("镍不在仓单数据中")
        raw_value = get_wrt_from_cu_df(cu_df)
        obs_date = obs_date_data
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        return

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source_confidence=1.0, source='AKShare_SHFE_warehouse_receipt')
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")


if __name__ == "__main__":
    main()
