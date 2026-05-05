#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_澳煤进口盈亏.py
因子: JM_COST_AU_PROFIT = 澳煤进口盈亏

公式: JM_COST_AU_PROFIT = 澳煤进口盈亏（元/吨）

当前状态: [⛔永久跳过]
- L1: 无免费数据源（澳煤进口盈亏需普氏报价）
- L2: 无备源
- L3: 付费订阅: 普氏能源（年费）
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback

SYMBOL = "JM"
FACTOR_CODE = "JM_COST_AU_PROFIT"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    # L1-L3: 无免费数据源（澳煤进口盈亏需普氏报价，普氏年费）
    print(f"[跳过] {FACTOR_CODE} 无免费数据源（付费订阅:普氏能源）")

    # L4: DB历史最新值回补
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
