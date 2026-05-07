#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I_铁矿石现货价.py
因子: I_SPT_SPOT = 铁矿石现货价（元/吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- L1: AKShare futures_spot_price(date, vars_list=["I"]) — 铁矿石现货价
- L2: 无备源（futures_spot_price 是唯一天然现货价接口）
- L4: save_l4_fallback() DB历史最新值回补

已验证: futures_spot_price(date='20260430', vars_list=['I']) 返回 spot_price=787.56
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
from datetime import timedelta

FCODE = "I_SPT_SPOT"
SYM = "I"
BOUNDS = (200, 2000)  # 铁矿石现货价合理范围（元/吨）
BACKOFF_DAYS = 15

# futures_spot_price 参数变体
SPOT_SYM_ALTERNATIVES = ["I", "i", "铁矿石", "铁矿"]


def fetch_l1(obs_date):
    """L1: futures_spot_price 直接返回现货价"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        for sym in SPOT_SYM_ALTERNATIVES:
            try:
                df = ak.futures_spot_price(date=date_str, vars_list=[sym])
                if df is not None and len(df) > 0:
                    row = df.iloc[0]
                    val = float(row['spot_price'])
                    print(f"  [L1 backoff {backoff}] {date_str} sym={sym}: spot_price={val:.2f}")
                    if BOUNDS[0] <= val <= BOUNDS[1]:
                        return val, try_date
                    else:
                        print(f"  [L1 backoff {backoff}] {val:.2f} out of {BOUNDS}")
            except Exception as e:
                print(f"  [L1 backoff {backoff}] futures_spot_price({date_str}, vars_list=['{sym}']): {type(e).__name__}: {str(e)[:80]}")
                continue
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: futures_spot_price
    raw_value, actual_obs = fetch_l1(obs_date)
    if raw_value is not None:
        save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=1.0, source='akshare_spot_price')
        print(f"[OK] {FCODE}={raw_value:.2f} obs={actual_obs}")
        return

    print("[L1 FAIL] futures_spot_price failed, trying L2...")

    # L2: 无备源（原因：现货价唯一天然接口即 futures_spot_price，无其他免费替代源）
    print("[L2 SKIP] 无备源，futures_spot_price 是唯一免费现货价接口")

    print("[L2 FAIL] no backup source, trying L4...")

    # L4: DB fallback
    save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
