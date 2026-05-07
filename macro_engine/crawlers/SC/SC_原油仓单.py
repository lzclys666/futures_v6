#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC_原油仓单.py
因子: SC_STK_WARRANT = 原油仓单（手）

公式: INE原油仓单总量

当前状态: [⛔永久跳过]
- L1: AKShare futures_warehouse_receipt_shfe — 无原油品种（原油在INE非SHFE）
- L2: AKShare futures_inventory_em — 无原油品种
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "SC_STK_WARRANT"
SYM = "SC"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 原油仓单无免费数据源，INE原油不在AKShare标准仓单接口中")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
