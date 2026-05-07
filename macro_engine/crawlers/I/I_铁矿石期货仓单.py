#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I_铁矿石期货仓单.py
因子: I_STK_WARRANT = 大商所铁矿石仓单库存

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: AKShare futures_warehouse_receipt_dce(date) — DCE仓单数据 → JSONDecodeError(DCE反爬)
- L2: AKShare futures_inventory_em(symbol="铁矿石") — 东方财富铁矿石库存
- L4: save_l4_fallback() DB历史最新值回补

已验证: futures_inventory_em(symbol='铁矿石') 返回日期/库存/增减三列，最新值约3650
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

FCODE = "I_STK_WARRANT"
SYM = "I"
BOUNDS = (0, 10000)  # 仓单合理范围（东方财富库存单位）
BACKOFF_DAYS = 15


def fetch_l1(obs_date):
    """L1: DCE仓单数据（当前已知JSONDecodeError，保留代码待恢复）"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            df = ak.futures_warehouse_receipt_dce(date=date_str)
            if df is None or len(df) == 0:
                print(f"  [L1 backoff {backoff}] {date_str}: empty result")
                continue
            # Try to find iron ore column
            i_col = None
            for c in df.columns:
                cs = str(c).lower()
                if 'i' == cs or '铁矿' in cs or 'iron' in cs:
                    i_col = c
                    break
            if i_col is None and len(df.columns) >= 2:
                i_col = df.columns[-1]
            if i_col:
                val = df.iloc[-1][i_col]
                if isinstance(val, str):
                    val = val.replace(',', '').strip()
                val = float(val)
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    print(f"  [L1 backoff {backoff}] {date_str}: {val:.0f}")
                    return val, try_date
        except Exception as e:
            print(f"  [L1 backoff {backoff}] futures_warehouse_receipt_dce({date_str}): {type(e).__name__}: {str(e)[:80]}")
            continue
    return None, None


def fetch_l2(obs_date):
    """L2: 东方财富铁矿石库存"""
    for sym in ["铁矿石", "铁矿石(澳)", "铁矿"]:
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
                print(f"[L2] {sym} {actual_date}: {val:.0f}")
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

    # L1: DCE warehouse receipt (currently broken)
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
