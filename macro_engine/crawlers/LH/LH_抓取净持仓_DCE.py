#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LH_抓取净持仓_DCE.py
因子: LH_POS_NET = 生猪期货前20净持仓（手）

公式: sum(持买仓量) - sum(持卖仓量) across all LH contracts top 20

当前状态: [✅正常]
- L1: Playwright 抓取 DCE 持仓排名页面（绕过 412 反爬）
- L2: AKShare futures_dce_position_rank（备用，同样可能被 412 阻断）
- L4: save_l4_fallback() DB 历史最新值回补

数据源: DCE 大连商品交易所官网持仓排名
浏览器自动化: Playwright chromium headless
"""

import sys
import os
import datetime

sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))

from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
from dce_scraper import fetch_dce_position_rank, compute_net_position

FCODE = "LH_POS_NET"
SYM = "LH"
BOUNDS = (-200000, 200000)  # 净持仓合理范围（手）
BACKOFF_DAYS = 15


def fetch(obs_date):
    """
    获取生猪前20净持仓，自动回退最多 BACKOFF_DAYS 个自然日找最近交易日
    返回: (net_position, actual_obs_date)
    """
    for backoff in range(BACKOFF_DAYS):
        try_date = obs_date - datetime.timedelta(days=backoff)
        date_str = try_date.strftime('%Y%m%d')

        print(f"  [backoff {backoff}] 尝试 {date_str}...")
        df = fetch_dce_position_rank(date_str, SYM, use_cache=True)

        if df is None or df.empty:
            print(f"  [backoff {backoff}] {date_str}: 无数据")
            continue

        net = compute_net_position(df)
        if net is None:
            print(f"  [backoff {backoff}] {date_str}: 无法计算净持仓")
            continue

        print(f"  [backoff {backoff}] {date_str}: 净持仓={net:.0f}")
        return float(net), try_date

    raise ValueError(f"DCE 持仓排名抓取失败，已回退 {BACKOFF_DAYS} 天")


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: Playwright 抓取 DCE
    try:
        raw_value, actual_obs = fetch(obs_date)
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {e}")
        # L4: 历史最新值回补
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    # 合理性校验
    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FCODE}={raw_value:.0f} out of {BOUNDS}, fall back to L4")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    # 写入数据库
    save_to_db(FCODE, SYM, pub_date, actual_obs, raw_value,
               source_confidence=1.0, source='DCE_Playwright')
    print(f"[OK] {FCODE}={raw_value:.0f} obs={actual_obs}")


if __name__ == "__main__":
    main()
