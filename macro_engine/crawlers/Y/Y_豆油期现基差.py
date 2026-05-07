#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Y_豆油期现基差.py
因子: Y_SPD_BASIS = 豆油期现基差（元/吨）

公式: 现货价 - 期货主力合约收盘价

当前状态: ✅正常
- L1: AKShare futures_spot_price(date, vars_list=['Y']) — 直接返回基差(dom_basis)
- L2: 手动计算 = spot_price - dominant_contract_price
- L4: save_l4_fallback() DB历史最新值回补

已验证: futures_spot_price(date='20260429', vars_list=['Y']) 返回 spot=8654, futures=8573, basis=81
注意: vars_list 必须用大写 'Y'，小写 'y' / '豆油' 均返回空
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
from datetime import timedelta

FCODE = "Y_SPD_BASIS"
SYM = "Y"
BOUNDS = (-5000, 5000)  # 基差合理范围（元/吨）
BACKOFF_DAYS = 15


def fetch_l1(obs_date):
    """L1: futures_spot_price 直接返回基差"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=["Y"])
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                spot = float(row['spot_price'])
                futures = float(row['dominant_contract_price'])
                # dom_basis = futures - spot, 基差 = spot - futures
                basis = spot - futures
                print("  [L1 backoff %d] %s: spot=%.2f, futures=%.2f, basis=%.2f" % (backoff, date_str, spot, futures, basis))
                if BOUNDS[0] <= basis <= BOUNDS[1]:
                    return basis, try_date
                else:
                    print("  [L1 backoff %d] basis=%.2f out of %s" % (backoff, basis, BOUNDS))
        except Exception as e:
            print("  [L1 backoff %d] futures_spot_price(%s): %s: %s" % (backoff, date_str, type(e).__name__, str(e)[:80]))
            continue
    return None, None


def fetch_l2(obs_date):
    """L2: 手动计算 = 现货价 - 期货主力收盘价"""
    spot_price = None
    futures_price = None

    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=["Y"])
            if df is not None and len(df) > 0:
                row = df.iloc[0]
                spot_price = float(row['spot_price'])
                futures_price = float(row['dominant_contract_price'])
                print("  [L2 backoff %d] %s: spot=%.2f, futures=%.2f" % (backoff, date_str, spot_price, futures_price))
                break
        except Exception as e:
            print("  [L2 backoff %d] spot(%s): %s: %s" % (backoff, date_str, type(e).__name__, str(e)[:80]))
            continue

    if spot_price is None or futures_price is None:
        return None, None

    basis = spot_price - futures_price
    print("  [L2] basis = %.2f - %.2f = %.2f" % (spot_price, futures_price, basis))
    if BOUNDS[0] <= basis <= BOUNDS[1]:
        return basis, obs_date
    else:
        print("[L2] basis=%.2f out of %s" % (basis, BOUNDS))
        return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print("=== %s === pub=%s obs=%s" % (FCODE, pub_date, obs_date))

    # L1: futures_spot_price 直接返回基差
    raw_value, actual_obs = fetch_l1(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=1.0, source='akshare_spot_price')
        print("[OK] %s=%.2f obs=%s" % (FCODE, raw_value, actual_obs))
        return

    print("[L1 FAIL] futures_spot_price failed, trying L2...")

    # L2: 手动计算
    raw_value, actual_obs = fetch_l2(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=0.9, source='akshare_calc_basis')
        print("[OK] %s=%.2f obs=%s" % (FCODE, raw_value, actual_obs))
        return

    print("[L2 FAIL] manual calculation failed, trying L4...")

    # L4: DB fallback
    save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
