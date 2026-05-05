#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M_抓取仓单.py
因子: M_STK_WARRANT = 豆粕仓单（CZCE厂库交割）

公式: M_STK_WARRANT = CZCE豆粕仓单数量（手）

当前状态: [⛔永久跳过]
- CZCE豆粕采用厂库交割制度，无公开仓单数据
- 实际M_STK_WARRANT由M_抓取库存.py通过AKShare futures_inventory_em采集
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, get_pit_dates, save_l4_fallback

FACTOR_CODE = "M_STK_WARRANT"
SYMBOL = "M"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print("[⛔永久跳过] CZCE豆粕(M)厂库交割制度，无公开仓单数据")
    print("[说明] M_STK_WARRANT 由 M_抓取库存.py (futures_inventory_em) 采集")
    # 不写NULL占位符（SOP§7）
    return 0


if __name__ == "__main__":
    sys.exit(main())
