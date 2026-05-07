#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LH_生猪仓单.py
因子: LH_STK_WARRANT = 生猪仓单（手）

公式: 大商所生猪仓单总量

当前状态: [⛔永久跳过]
- L1: AKShare futures_warehouse_receipt_dce — 生猪仓单不在标准品种列表中
- L2: AKShare futures_inventory_em — 无生猪品种
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "LH_STK_WARRANT"
SYM = "LH"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 生猪仓单无免费数据源，AKShare无对应接口")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
