#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Y_进口大豆CNF价.py
因子: Y_COST_CNF = 进口大豆CNF到岸价（美元/吨）
当前状态: [⛔永久跳过]
- 原因: 付费订阅(卓创资讯)，无免费数据源
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "Y_COST_CNF"
SYM = "Y"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 付费订阅(卓创资讯)，无免费数据源")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
