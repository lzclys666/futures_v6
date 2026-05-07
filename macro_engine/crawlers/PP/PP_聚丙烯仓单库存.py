#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP_聚丙烯仓单库存.py
因子: PP_STK_WARRANT = 大商所聚丙烯仓单库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: AKShare futures_warehouse_receipt_dce(date) — DCE仓单数据
- L2: AKShare futures_inventory_em(symbol="聚丙烯") — 东方财富聚丙烯库存
- L4: save_l4_fallback() DB历史最新值回补

已验证: futures_inventory_em 返回日期/库存/增减三列，最新值约15000吨
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

FCODE = "PP_STK_WARRANT"
SYM = "PP"
BOUNDS = (0, 500000)  # 仓单合理范围（吨）
BACKOFF_DAYS = 15


def fetch_l1(obs_date):
    """L1: DCE仓单数据"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            df = ak.futures_warehouse_receipt_dce(date=date_str)
            if df is not None and len(df) > 0:
                # Find PP-related column
                pp_col = None
                for c in df.columns:
                    if 'pp' in str(c).lower() or '聚丙' in str(c):
                        pp_col = c
                        break
                if pp_col is None:
                    # Try last numeric column
                    for c in df.columns:
                        if any(x in str(c) for x in ['仓单', '库存', '吨']):
                            pp_col = c
                            break
                if pp_col is None and len(df.columns) >= 2:
                    pp_col = df.columns[-1]

                if pp_col:
                    val = df.iloc[-1][pp_col]
                    if isinstance(val, str):
                        val = val.replace(',', '').strip()
                    val = float(val)
                    if BOUNDS[0] <= val <= BOUNDS[1]:
                        print(f"  [L1 backoff {backoff}] {date_str}: {val:.0f} 吨")
                        return val, try_date
                    else:
                        print(f"  [L1 backoff {backoff}] {date_str}: {val:.0f} out of {BOUNDS}")
        except Exception as e:
            print(f"  [L1 backoff {backoff}] futures_warehouse_receipt_dce({date_str}): {type(e).__name__}: {str(e)[:80]}")
            continue
    return None, None


def fetch_l2(obs_date):
    """L2: 东方财富聚丙烯库存"""
    try:
        print("[L2] futures_inventory_em(symbol='聚丙烯')...")
        df = ak.futures_inventory_em(symbol="聚丙烯")
        if df is None or len(df) == 0:
            print("[L2] empty result")
            return None, None

        # Columns: 日期, 库存, 增减 (garbled encoding but positional)
        date_col = df.columns[0]
        inv_col = df.columns[1]

        # Find closest date to obs_date
        df[date_col] = pd.to_datetime(df[date_col])
        obs_dt = pd.Timestamp(obs_date)
        # Filter to dates <= obs_date
        df_valid = df[df[date_col] <= obs_dt]
        if len(df_valid) == 0:
            print("[L2] no data on or before obs_date")
            return None, None

        row = df_valid.iloc[-1]
        val = float(row[inv_col])
        actual_date = row[date_col].date()
        if BOUNDS[0] <= val <= BOUNDS[1]:
            print(f"[L2] {actual_date}: {val:.0f} 吨")
            return val, actual_date
        else:
            print(f"[L2] {val:.0f} out of {BOUNDS}")
    except Exception as e:
        print(f"[L2] {type(e).__name__}: {str(e)[:100]}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: DCE warehouse receipt
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
