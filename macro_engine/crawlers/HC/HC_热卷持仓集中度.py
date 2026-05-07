#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HC_热卷持仓集中度.py
因子: HC_POS_CONC = 热卷前20持仓集中度差（多头CR10 - 空头CR10，%）

公式: HC_POS_CONC = (top10_long / total_long - top10_short / total_short) * 100

当前状态: ✅正常
- L1: AKShare get_shfe_rank_table(date) — 上期所持仓排名
- L4: save_l4_fallback() DB历史最新值回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

FCODE = "HC_POS_CONC"
SYM = "HC"
BOUNDS = (-30, 30)  # CR10差值合理范围（%）
BACKOFF_DAYS = 15


def fetch(obs_date):
    """L1: get_shfe_rank_table 计算HC持仓集中度"""
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')
        try:
            result = ak.get_shfe_rank_table(date=date_str)
            if not isinstance(result, dict):
                continue
            hc_keys = [k for k in result if k.lower().startswith('hc')]
            if not hc_keys:
                continue
            df = result[hc_keys[0]]
            if not isinstance(df, pd.DataFrame) or len(df) == 0:
                continue

            total_long = float(df['long_open_interest'].sum())
            total_short = float(df['short_open_interest'].sum())
            if total_long == 0 or total_short == 0:
                continue

            top10_long = float(df.head(10)['long_open_interest'].sum())
            top10_short = float(df.head(10)['short_open_interest'].sum())
            cr10_long = top10_long / total_long * 100
            cr10_short = top10_short / total_short * 100
            cr10_diff = cr10_long - cr10_short

            print(f"  [L1 backoff {backoff}] {date_str} {hc_keys[0]}: "
                  f"CR10L={cr10_long:.2f}% CR10S={cr10_short:.2f}% diff={cr10_diff:.2f}%")
            if BOUNDS[0] <= cr10_diff <= BOUNDS[1]:
                return cr10_diff
            else:
                print(f"  [L1 backoff {backoff}] {cr10_diff:.2f} out of {BOUNDS}")
        except Exception as e:
            print(f"  [L1 backoff {backoff}] {date_str}: {type(e).__name__}: {str(e)[:80]}")
            continue
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value = fetch(obs_date)
        if raw_value is None:
            print(f"[L1] {FCODE}: 所有尝试失败")
            save_l4_fallback(FCODE, SYM, pub_date, obs_date)
            return
        save_to_db(FCODE, SYM, pub_date, obs_date, raw_value,
                   source_confidence=1.0, source='akshare_shfe_rank')
        print(f"[OK] {FCODE}={raw_value:.2f} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {type(e).__name__}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
