#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭期货仓单.py
因子: J_STK_WARRANT = 焦炭期货仓单库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: AKShare futures_warehouse_receipt_dce(date, symbol='焦炭') — DCE仓单 → JSONDecodeError(DCE反爬)
- L2: AKShare futures_inventory_em(symbol='焦炭') — 东方财富焦炭库存 → 正常
- L4: save_l4_fallback() DB历史最新值回补

已验证: futures_inventory_em(symbol='焦炭') 返回日期/库存/增减三列，最新值约1230吨
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

FCODE = "J_STK_WARRANT"
SYM = "J"
BOUNDS = (0, 100000)  # 仓单合理范围（吨）
BACKOFF_DAYS = 15


def fetch_l1(obs_date):
    """L1: DCE仓单数据（当前已知失效）"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            df = ak.futures_warehouse_receipt_dce(date=date_str)
            if df is None or len(df) == 0:
                print(f"  [L1 backoff {backoff}] {date_str}: empty result")
                continue
            # Find J-related row
            for _, row in df.iterrows():
                row_str = ' '.join(str(v) for v in row.values)
                if '焦炭' in row_str or row_str.strip().startswith('J'):
                    for val in row.values:
                        if isinstance(val, (int, float)) and not pd.isna(val) and val > 0:
                            if BOUNDS[0] <= val <= BOUNDS[1]:
                                print(f"  [L1 backoff {backoff}] {date_str}: {val:.0f}")
                                return float(val), try_date
        except Exception as e:
            print(f"  [L1 backoff {backoff}] futures_warehouse_receipt_dce({date_str}): {type(e).__name__}: {str(e)[:80]}")
            continue
    return None, None


def fetch_l2(obs_date):
    """L2: 东方财富焦炭库存"""
    for sym in ["焦炭", "j", "J"]:
        try:
            print(f"[L2] futures_inventory_em(symbol='{sym}')...")
            df = ak.futures_inventory_em(symbol=sym)
            if df is None or len(df) == 0:
                print(f"[L2] empty result for '{sym}'")
                continue

            date_col = df.columns[0]
            inv_col = df.columns[1]

            df[date_col] = pd.to_datetime(df[date_col])
            obs_dt = pd.Timestamp(obs_date)
            df_valid = df[df[date_col] <= obs_dt]
            if len(df_valid) == 0:
                print(f"[L2] no data on or before obs_date for '{sym}'")
                continue

            row = df_valid.iloc[-1]
            val = float(row[inv_col])
            actual_date = row[date_col].date()
            if BOUNDS[0] <= val <= BOUNDS[1]:
                print(f"[L2] {sym} {actual_date}: {val:.0f} 吨")
                return val, actual_date
            else:
                print(f"[L2] {sym} {val:.0f} out of {BOUNDS}")
        except Exception as e:
            print(f"[L2] {sym}: {type(e).__name__}: {str(e)[:100]}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: DCE warehouse receipt (known broken)
    raw_value, actual_obs = fetch_l1(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=1.0, source='akshare_dce_warehouse_receipt')
        print(f"[OK] {FCODE}={raw_value:.0f} obs={actual_obs}")
        return

    print("[L1 FAIL] DCE warehouse receipt failed, trying L2...")

    # L2: 东方财富库存
    raw_value, actual_obs = fetch_l2(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=0.9, source='akshare_inventory_em')
        print(f"[OK] {FCODE}={raw_value:.0f} obs={actual_obs}")
        return

    print("[L2 FAIL] 东方财富库存 failed, trying L4...")

    # L4: DB fallback
    save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
