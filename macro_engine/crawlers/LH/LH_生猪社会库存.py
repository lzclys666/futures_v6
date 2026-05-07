#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LH_生猪社会库存.py
因子: LH_STK_SOCIAL = 生猪社会库存（万头）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: AKShare — 无生猪社会库存接口
- L2: 国家统计局 — 月度数据，无日频接口
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "LH_STK_SOCIAL"
SYM = "LH"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 生猪社会库存无免费日频数据源")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
