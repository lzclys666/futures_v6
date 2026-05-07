#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC_原油期货净持仓.py
因子: SC_POS_NET = 原油期货前20净持仓（手）

公式: sum(long_open_interest_top20) - sum(short_open_interest_top20) across all SC contracts

当前状态: [⛔永久跳过]
- L1: AKShare get_rank_sum_daily(vars_list=['SC']) — INE不发布持仓排名数据，返回空DataFrame
- L2: AKShare get_ine_daily — 仅有open_interest总量，无多空分拆
- 不写占位符，不做L4回补

备注: INE（上海国际能源交易中心）不公开发布会员持仓排名数据，
因此无法获取原油期货前20多空持仓明细。get_rank_sum_daily / get_rank_sum
均返回空DataFrame。
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "SC_POS_NET"
SYM = "SC"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: INE不发布会员持仓排名数据，AKShare无可用接口")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
