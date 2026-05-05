#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Y_豆油期货仓单.py
因子: Y_STK_WARRANT = 大商所豆油仓单（手）
当前状态: [⛔永久跳过]
- 原因: DCE仓单接口待验证
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "Y_STK_WARRANT"
SYM = "Y"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: DCE仓单接口待验证")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
