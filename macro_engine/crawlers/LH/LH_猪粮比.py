#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LH_猪粮比.py
因子: LH_SPD_PIG_GRAIN = 猪粮比价（倍）

公式: 生猪价格 / 玉米价格

当前状态: [⛔永久跳过]
- L1: AKShare — 无猪粮比直接接口
- L2: 手动计算需要生猪现货价+玉米现货价，两个数据源均不稳定
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "LH_SPD_PIG_GRAIN"
SYM = "LH"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 猪粮比无免费日频数据源，计算依赖两个不稳定现货价")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
