#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LH_生猪出栏量.py
因子: LH_PROD_OUTPUT = 生猪出栏量（万头）

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- L1: AKShare — 无生猪出栏量日频接口
- L2: 国家统计局 — 季度数据，无日频接口
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "LH_PROD_OUTPUT"
SYM = "LH"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 生猪出栏量无免费日频数据源（国家统计局仅季度发布）")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
