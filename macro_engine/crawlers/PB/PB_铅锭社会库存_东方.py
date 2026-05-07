#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB_铅锭社会库存_东方.py
因子: PB_STK_INVENTORY = 铅锭社会库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_inventory_em(symbol='铅') — 东方财富铅库存
- L2: 无备源
- L3: save_l4_fallback() DB历史最新值回补

注: 与 PB_STK_SOCIAL 使用相同数据源，但因子代码不同（引擎配置要求）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "PB_STK_INVENTORY"
SYM = "PB"
BOUNDS = (0, 500000)  # 库存合理范围（吨）


def fetch(obs_date):
    """东方财富铅库存"""
    df = ak.futures_inventory_em(symbol="沪铅")
    if df is None or len(df) == 0:
        raise ValueError("empty result")

    date_col = df.columns[0]
    inv_col = df.columns[1]

    df[date_col] = pd.to_datetime(df[date_col])
    obs_dt = pd.Timestamp(obs_date)

    df_valid = df[df[date_col] <= obs_dt]
    if len(df_valid) == 0:
        df_valid = df

    row = df_valid.iloc[-1]
    val = float(row[inv_col])
    obs = row[date_col].date()
    print(f"  [L1] {obs}: {val:.0f} 吨")
    return val, obs


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value, actual_obs = fetch(obs_date)
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FCODE}={raw_value:.0f} out of {BOUNDS}, fall back to L4")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    if str(actual_obs) == str(pub_date):
        print(f"[PIT] obs_date=pub_date={actual_obs}, using L4")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=0.9, source='akshare_inventory_em')
    print(f"[OK] {FCODE}={raw_value:.0f} obs={actual_obs}")


if __name__ == "__main__":
    main()
