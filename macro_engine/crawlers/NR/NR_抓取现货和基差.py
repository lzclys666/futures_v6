#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NR_抓取现货和基差.py
因子: NR_SPD_BASIS = 20号胶期现基差

公式: NR_SPD_BASIS = NR现货价 - NR期货收盘价

当前状态: [⛔永久跳过]
- AKShare无NR(20号胶)现货价格数据
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates, save_l4_fallback

FACTOR_CODE = "NR_SPD_BASIS"
SYMBOL = "NR"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print("[⛔永久跳过] AKShare无NR(20号胶)现货价格数据")
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
