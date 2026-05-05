#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Y_CBOT豆油期货收盘价.py
因子: Y_FUT_CBOT_OIL = CBOT豆油期货收盘价（美分/磅）
当前状态: [⛔永久跳过]
- 原因: DCE接口待验证，无免费可靠源
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "Y_FUT_CBOT_OIL"
SYM = "Y"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: DCE接口待验证，无免费可靠源")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
