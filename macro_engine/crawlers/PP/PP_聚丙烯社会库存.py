#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP_聚丙烯社会库存.py
因子: PP_STK_INVENTORY = 聚丙烯社会库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_inventory_em(symbol='聚丙烯') — 东方财富聚丙烯库存
- L2: 无备源
- L3: save_l4_fallback() DB历史最新值回补

已验证: futures_inventory_em 返回日期/库存/增减三列，最新值约16000吨
注: 东方财富数据按交易日更新，返回最近交易日数据，可能与obs_date不完全一致
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "PP_STK_INVENTORY"
SYM = "PP"
BOUNDS = (0, 500000)  # 库存合理范围（吨）


def fetch(obs_date):
    """L1: 东方财富聚丙烯库存，取obs_date当天或之前最近的数据"""
    df = ak.futures_inventory_em(symbol="聚丙烯")
    if df is None or len(df) == 0:
        raise ValueError("empty result")

    date_col = df.columns[0]
    inv_col = df.columns[1]

    df[date_col] = pd.to_datetime(df[date_col])
    obs_dt = pd.Timestamp(obs_date)

    # 取obs_date当天或之前最近的数据
    df_valid = df[df[date_col] <= obs_dt]
    if len(df_valid) == 0:
        # 如果没有obs_date之前的数据，取最早的一条
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

    # L1: 东方财富库存
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

    # PIT check: obs_date must be before pub_date
    if str(actual_obs) == str(pub_date):
        print(f"[PIT] obs_date=pub_date={actual_obs}, 使用L4回补")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=0.9, source='akshare_inventory_em')
    print(f"[OK] {FCODE}={raw_value:.0f} obs={actual_obs}")


if __name__ == "__main__":
    main()
