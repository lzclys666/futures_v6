#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I_铁矿石期货净持仓.py
因子: I_POS_NET = 大商所铁矿石前20净持仓（手）

公式: sum(long_open_interest across all I contracts top 20) - sum(short_open_interest across all I contracts top 20)

当前状态: [BLOCKED] DCE反爬，等待AKShare修复
- L1: AKShare futures_dce_position_rank(date) — DCE持仓排名 → BadZipFile(DCE反爬)
- L2: AKShare get_dce_rank_table(date) — DCE持仓排名备选 → 超时/无响应
- L4: save_l4_fallback() DB历史最新值回补

尝试过的数据源及结果:
1. futures_dce_position_rank(date='20260430') → BadZipFile: File is not a zip file
2. get_dce_rank_table(date='20260430') → 超时无响应（进程被kill）
3. futures_warehouse_receipt_dce → JSONDecodeError（DCE全线反爬）

结论: DCE所有持仓排名接口均被反爬机制阻断，等待AKShare修复或DCE解除限制。
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

FCODE = "I_POS_NET"
SYM = "I"
BOUNDS = (-500000, 500000)  # 净持仓合理范围（手）
BACKOFF_DAYS = 15


def fetch_l1(obs_date):
    """L1: futures_dce_position_rank — DCE持仓排名（当前BadZipFile）"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            result = ak.futures_dce_position_rank(date=date_str)
            if not (isinstance(result, dict) and result):
                print(f"  [L1 backoff {backoff}] {date_str}: empty result")
                continue
            i_keys = [k for k in result if k.lower().startswith('i') and not k.lower().startswith('im')]
            if not i_keys:
                print(f"  [L1 backoff {backoff}] {date_str}: no I keys")
                continue
            total_long, total_short = 0.0, 0.0
            for k in i_keys:
                df = result[k]
                if not isinstance(df, pd.DataFrame):
                    continue
                long_col = None
                short_col = None
                for c in df.columns:
                    cl = str(c).lower()
                    if 'long' in cl or '买' in cl:
                        long_col = c
                    if 'short' in cl or '卖' in cl:
                        short_col = c
                if long_col and short_col:
                    total_long += pd.to_numeric(df[long_col], errors='coerce').sum()
                    total_short += pd.to_numeric(df[short_col], errors='coerce').sum()
            net = total_long - total_short
            if net != 0:
                print(f"  [L1 backoff {backoff}] {date_str}: long={total_long:.0f}, short={total_short:.0f}, net={net:.0f}")
                return float(net), try_date
        except Exception as e:
            print(f"  [L1 backoff {backoff}] futures_dce_position_rank({date_str}): {type(e).__name__}: {str(e)[:80]}")
            continue
    return None, None


def fetch_l2(obs_date):
    """L2: get_dce_rank_table — DCE持仓排名备选（当前超时）"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            result = ak.get_dce_rank_table(date=date_str)
            if not (isinstance(result, dict) and result):
                print(f"  [L2 backoff {backoff}] {date_str}: empty result")
                continue
            i_keys = [k for k in result if k.lower().startswith('i') and not k.lower().startswith('im')]
            if not i_keys:
                print(f"  [L2 backoff {backoff}] {date_str}: no I keys")
                continue
            total_long, total_short = 0.0, 0.0
            for k in i_keys:
                df = result[k]
                if not isinstance(df, pd.DataFrame):
                    continue
                long_col = None
                short_col = None
                for c in df.columns:
                    cl = str(c).lower()
                    if 'long' in cl or '买' in cl:
                        long_col = c
                    if 'short' in cl or '卖' in cl:
                        short_col = c
                if long_col and short_col:
                    total_long += pd.to_numeric(df[long_col], errors='coerce').sum()
                    total_short += pd.to_numeric(df[short_col], errors='coerce').sum()
            net = total_long - total_short
            if net != 0:
                print(f"  [L2 backoff {backoff}] {date_str}: long={total_long:.0f}, short={total_short:.0f}, net={net:.0f}")
                return float(net), try_date
        except Exception as e:
            print(f"  [L2 backoff {backoff}] get_dce_rank_table({date_str}): {type(e).__name__}: {str(e)[:80]}")
            continue
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print("[BLOCKED] DCE反爬，所有持仓排名接口均失效，跳过L1/L2直接L4...")

    # L1: DCE position rank (currently blocked)
    # raw_value, actual_obs = fetch_l1(obs_date)
    # if raw_value is not None:
    #     save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=1.0, source='akshare_dce_position_rank')
    #     print(f"[OK] {FCODE}={raw_value:.0f} obs={actual_obs}")
    #     return

    # L2: get_dce_rank_table (currently blocked)
    # raw_value, actual_obs = fetch_l2(obs_date)
    # if raw_value is not None:
    #     save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value, source_confidence=0.9, source='akshare_dce_rank_table')
    #     print(f"[OK] {FCODE}={raw_value:.0f} obs={actual_obs}")
    #     return

    # L4: DB fallback
    save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
