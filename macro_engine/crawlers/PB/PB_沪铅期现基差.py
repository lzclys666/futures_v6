#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB_沪铅期现基差.py
因子: PB_SPD_BASIS = 沪铅期现基差（元/吨）

公式: 主力合约收盘价 - 现货价格（期货升水为正）

当前状态: [✅正常]
- L1: AKShare futures_spot_price(vars_list=['PB']) → dom_basis 字段
- L4: save_l4_fallback() DB历史最新值回补

数据源: 生意社/期货日报 聚合的期现价格数据
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

FCODE = "PB_SPD_BASIS"
SYM = "PB"
BOUNDS = (-2000, 2000)  # 基差合理范围（元/吨）


def fetch(obs_date):
    """获取沪铅期现基差，自动回退最多30天找最近交易日"""
    for backoff in range(30):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=['PB'])
        except Exception as e:
            print(f"  [backoff {backoff}] {date_str}: {e}")
            continue

        if not isinstance(df, pd.DataFrame) or df.empty:
            print(f"  [backoff {backoff}] {date_str}: empty result")
            continue

        row = df.iloc[0]
        basis = float(row['dom_basis'])
        print(f"  [backoff {backoff}] {date_str}: spot={row['spot_price']}, dominant={row['dominant_contract']}@{row['dominant_contract_price']}, basis={basis}")
        return basis, try_date

    raise ValueError("futures_spot_price failed after 30 backoff attempts")


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: futures_spot_price
    try:
        raw_value, actual_obs = fetch(obs_date)
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FCODE}={raw_value:.2f} out of {BOUNDS}, fall back to L4")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=1.0, source='AKShare_futures_spot_price')
    print(f"[OK] {FCODE}={raw_value:.2f} obs={actual_obs}")


if __name__ == "__main__":
    main()
