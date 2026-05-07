#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LH_生猪期货净持仓.py
因子: LH_POS_NET = 生猪期货前20净持仓（手）

公式: sum(long_open_interest across all LH contracts top 20) - sum(short_open_interest across all LH contracts top 20)

当前状态: [⛔永久跳过]
- L1: AKShare get_dce_rank_table(date) — DCE网站412反爬，BadZipFile
- L2: AKShare futures_dce_position_rank — 同样被DCE反爬阻断
- 不写占位符，不做L4回补

备注: DCE（大连商品交易所）网站对爬虫实施412反爬策略，
get_dce_rank_table 和 futures_dce_position_rank 均返回 BadZipFile 错误。
此问题影响所有DCE品种（LH/PP/EG等），非脚本问题。
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "LH_POS_NET"
SYM = "LH"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: DCE网站412反爬，get_dce_rank_table返回BadZipFile")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
