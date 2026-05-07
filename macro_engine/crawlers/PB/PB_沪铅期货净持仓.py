#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB_沪铅期货净持仓.py
因子: PB_POS_NET = 上期所沪铅前20净持仓（手）

公式: sum(long_open_interest across all PB contracts top 20) - sum(short_open_interest across all PB contracts top 20)

当前状态: [✅正常]
- L1: AKShare get_shfe_rank_table(date="YYYYMMDD") — SHFE持仓排名前20
- L4: save_l4_fallback() DB历史最新值回补

已验证: get_shfe_rank_table(date="20260430") 返回 pb2605/pb2606/pb2607 三个合约
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

FCODE = "PB_POS_NET"
SYM = "PB"
BOUNDS = (-50000, 50000)  # 净持仓合理范围（手）


def fetch(obs_date):
    """获取沪铅前20净持仓，自动回退最多30个自然日找最近交易日"""
    for backoff in range(30):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            result = ak.get_shfe_rank_table(date=date_str)
        except Exception as e:
            print(f"  [backoff {backoff}] get_shfe_rank_table({date_str}): {e}")
            continue

        if not (isinstance(result, dict) and result):
            print(f"  [backoff {backoff}] {date_str}: empty result")
            continue

        pb_keys = [k for k in result if k.startswith('pb')]
        if not pb_keys:
            print(f"  [backoff {backoff}] {date_str}: no PB keys in result")
            continue

        total_long = 0.0
        total_short = 0.0
        for k in pb_keys:
            df = result[k]
            if not isinstance(df, pd.DataFrame):
                print(f"  [backoff {backoff}] {date_str}/{k}: expected DataFrame, got {type(df).__name__}")
                continue
            if 'long_open_interest' not in df.columns or 'short_open_interest' not in df.columns:
                print(f"  [backoff {backoff}] {date_str}/{k}: missing OI columns, got {df.columns.tolist()}")
                continue
            long_sum = df['long_open_interest'].sum()
            short_sum = df['short_open_interest'].sum()
            total_long += long_sum
            total_short += short_sum

        net = total_long - total_short
        print(f"  [backoff {backoff}] {date_str}: long={total_long}, short={total_short}, net={net}")
        return float(net), try_date

    raise ValueError("get_shfe_rank_table failed after 30 backoff attempts — no PB data on any recent trading day")


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: SHFE rank table
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

    save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=1.0, source='AKShare_SHFE_rank')
    print(f"[OK] {FCODE}={raw_value:.0f} obs={actual_obs}")


if __name__ == "__main__":
    main()
