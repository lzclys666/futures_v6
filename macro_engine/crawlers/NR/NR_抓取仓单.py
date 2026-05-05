#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NR_抓取仓单.py
因子: NR_STK_WARRANT = 20号胶仓单

公式: NR_STK_WARRANT = INE20号胶仓单数量（吨）

当前状态: [⛔永久跳过]
- INE无公开仓单数据接口
- NR_INV_TOTAL已覆盖库存数据
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates, save_l4_fallback

FACTOR_CODE = "NR_STK_WARRANT"
SYMBOL = "NR"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print("[⛔永久跳过] INE无公开仓单数据，NR_INV_TOTAL已覆盖")
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
