#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HC_热卷期现基差.py
因子: HC_SPD_BASIS = 热卷期现基差（元/吨）

公式: 现货价 - 期货主力合约收盘价

当前状态: ✅正常
- L1: AKShare futures_spot_price(date, vars_list=["HC"]) — 直接返回基差
- L2: 手动计算 = 现货价 - futures_main_sina("HC0")收盘价
- L4: save_l4_fallback() DB历史最新值回补

已验证: futures_spot_price(date='20260430', vars_list=['HC']) 返回 spot=3424, futures=3425, basis=-1
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

FCODE = "HC_SPD_BASIS"
SYM = "HC"
BOUNDS = (-5000, 5000)  # 基差合理范围（元/吨）
BACKOFF_DAYS = 15

# futures_spot_price 参数变体
SPOT_SYM_ALTERNATIVES = ["HC", "hc", "热轧卷板", "热卷"]


def fetch_l1(obs_date):
    """L1: futures_spot_price 直接返回基差"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        for sym in SPOT_SYM_ALTERNATIVES:
            try:
                df = ak.futures_spot_price(date=date_str, vars_list=[sym])
                if df is not None and len(df) > 0:
                    row = df.iloc[0]
                    spot = float(row['spot_price'])
                    futures = float(row['dominant_contract_price'])
                    basis = spot - futures
                    print(f"  [L1 backoff {backoff}] {date_str} sym={sym}: spot={spot:.2f}, futures={futures:.2f}, basis={basis:.2f}")
                    if BOUNDS[0] <= basis <= BOUNDS[1]:
                        return basis, try_date
                    else:
                        print(f"  [L1 backoff {backoff}] basis={basis:.2f} out of {BOUNDS}")
            except Exception as e:
                print(f"  [L1 backoff {backoff}] futures_spot_price({date_str}, vars_list=['{sym}']): {type(e).__name__}: {str(e)[:80]}")
                continue
    return None, None


def fetch_l2(obs_date):
    """L2: 手动计算 = 现货价 - 期货主力收盘价"""
    # Get futures price
    futures_price = None
    try:
        print("[L2] futures_main_sina('HC0')...")
        df = ak.futures_main_sina(symbol="HC0")
        if df is not None and len(df) > 0:
            close_col = None
            for c in df.columns:
                if 'close' in str(c).lower() or '收盘' in str(c):
                    close_col = c
                    break
            if close_col is None:
                close_col = df.columns[4] if len(df.columns) > 4 else df.columns[-1]
            futures_price = float(df.iloc[-1][close_col])
            print(f"  [L2] futures close: {futures_price:.2f}")
    except Exception as e:
        print(f"[L2] futures_main_sina: {type(e).__name__}: {str(e)[:100]}")

    if futures_price is None:
        return None, None

    # Get spot price
    spot_price = None
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        for sym in SPOT_SYM_ALTERNATIVES:
            try:
                df = ak.futures_spot_price(date=date_str, vars_list=[sym])
                if df is not None and len(df) > 0:
                    spot_price = float(df.iloc[0]['spot_price'])
                    print(f"  [L2] spot price ({date_str} sym={sym}): {spot_price:.2f}")
                    break
            except Exception as e:
                print(f"  [L2] spot({date_str}, {sym}): {type(e).__name__}: {str(e)[:80]}")
                continue
        if spot_price is not None:
            break

    if spot_price is None:
        return None, None

    basis = spot_price - futures_price
    print(f"  [L2] basis = {spot_price:.2f} - {futures_price:.2f} = {basis:.2f}")
    if BOUNDS[0] <= basis <= BOUNDS[1]:
        return basis, obs_date
    else:
        print(f"[L2] basis={basis:.2f} out of {BOUNDS}")
        return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: futures_spot_price 直接返回基差
    raw_value, actual_obs = fetch_l1(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=1.0, source='akshare_spot_price')
        print(f"[OK] {FCODE}={raw_value:.2f} obs={actual_obs}")
        return

    print("[L1 FAIL] futures_spot_price failed, trying L2...")

    # L2: 手动计算
    raw_value, actual_obs = fetch_l2(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=0.9, source='akshare_calc_basis')
        print(f"[OK] {FCODE}={raw_value:.2f} obs={actual_obs}")
        return

    print("[L2 FAIL] manual calculation failed, trying L4...")

    # L4: DB fallback
    save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
