#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC_裂解价差.py
因子: SC_SPD_CRACK = 原油裂解价差（元/桶）

公式: 成品油价格 - 原油价格

当前状态: [⛔永久跳过]
- L1: AKShare — 无裂解价差直接接口
- L2: 手动计算需要成品油现货价+原油现货价，成品油数据无免费源
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "SC_SPD_CRACK"
SYM = "SC"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 裂解价差无免费数据源，计算依赖成品油价格（无免费接口）")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
