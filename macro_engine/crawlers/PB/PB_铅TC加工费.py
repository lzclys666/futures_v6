#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB_铅TC加工费.py
因子: PB_MACRO_TC = 铅矿加工费（美元/吨）
当前状态: [⛔永久跳过]
- 原因: 付费订阅（SMM），无免费数据源
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "PB_MACRO_TC"
SYM = "PB"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 付费订阅(SMM)，无免费数据源")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
