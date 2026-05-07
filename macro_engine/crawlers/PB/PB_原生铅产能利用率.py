#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB_原生铅产能利用率.py
因子: PB_PROD_CAPACITY = 原生铅产能利用率（%）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: AKShare — 无原生铅产能利用率接口
- L2: SMM/安泰科 — 付费订阅
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "PB_PROD_CAPACITY"
SYM = "PB"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 原生铅产能利用率无免费数据源（SMM/安泰科付费）")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
