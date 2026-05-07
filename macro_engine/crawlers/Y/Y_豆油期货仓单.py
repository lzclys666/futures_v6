#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Y_豆油期货仓单.py
因子: Y_STK_WARRANT = 大商所豆油仓单库存（吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: AKShare futures_warehouse_receipt_dce(date) — DCE仓单数据 → JSONDecodeError(DCE反爬)
- L2: AKShare futures_inventory_em(symbol="豆油") — 东方财富豆油库存
- L4: save_l4_fallback() DB历史最新值回补

已验证: futures_inventory_em 返回日期/库存/增减三列，最新值约27720吨
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

FCODE = "Y_STK_WARRANT"
SYM = "Y"
BOUNDS = (0, 500000)  # 仓单合理范围（吨）
BACKOFF_DAYS = 15


def fetch_l1(obs_date):
    """L1: DCE仓单数据（DCE反爬，大概率失败）"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            df = ak.futures_warehouse_receipt_dce(date=date_str)
            if df is not None and len(df) > 0:
                y_col = None
                for c in df.columns:
                    if 'y' in str(c).lower() or '豆油' in str(c):
                        y_col = c
                        break
                if y_col is None and len(df.columns) >= 2:
                    y_col = df.columns[-1]
                if y_col:
                    val = df.iloc[-1][y_col]
                    if isinstance(val, str):
                        val = val.replace(',', '').strip()
                    val = float(val)
                    if BOUNDS[0] <= val <= BOUNDS[1]:
                        print("  [L1 backoff %d] %s: %.0f 吨" % (backoff, date_str, val))
                        return val, try_date
                    else:
                        print("  [L1 backoff %d] %s: %.0f out of %s" % (backoff, date_str, val, BOUNDS))
        except Exception as e:
            print("  [L1 backoff %d] futures_warehouse_receipt_dce(%s): %s: %s" % (backoff, date_str, type(e).__name__, str(e)[:80]))
            continue
    return None, None


def fetch_l2(obs_date):
    """L2: 东方财富豆油库存"""
    try:
        print("[L2] futures_inventory_em(symbol='豆油')...")
        df = ak.futures_inventory_em(symbol="豆油")
        if df is None or len(df) == 0:
            print("[L2] empty result")
            return None, None

        date_col = df.columns[0]
        inv_col = df.columns[1]

        df[date_col] = pd.to_datetime(df[date_col])
        obs_dt = pd.Timestamp(obs_date)
        df_valid = df[df[date_col] <= obs_dt]
        if len(df_valid) == 0:
            print("[L2] no data on or before obs_date")
            return None, None

        row = df_valid.iloc[-1]
        val = float(row[inv_col])
        actual_date = row[date_col].date()
        if BOUNDS[0] <= val <= BOUNDS[1]:
            print("[L2] %s: %.0f 吨" % (actual_date, val))
            return val, actual_date
        else:
            print("[L2] %.0f out of %s" % (val, BOUNDS))
    except Exception as e:
        print("[L2] %s: %s" % (type(e).__name__, str(e)[:100]))
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print("=== %s === pub=%s obs=%s" % (FCODE, pub_date, obs_date))

    # L1: DCE warehouse receipt
    raw_value, actual_obs = fetch_l1(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=1.0, source='akshare_dce_warehouse_receipt')
        print("[OK] %s=%.0f obs=%s" % (FCODE, raw_value, actual_obs))
        return

    print("[L1 FAIL] DCE warehouse receipt failed, trying L2...")

    # L2: 东方财富库存
    raw_value, actual_obs = fetch_l2(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=0.9, source='akshare_inventory_em')
        print("[OK] %s=%.0f obs=%s" % (FCODE, raw_value, actual_obs))
        return

    print("[L2 FAIL] 东方财富库存 failed, trying L4...")

    # L4: DB fallback
    save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
