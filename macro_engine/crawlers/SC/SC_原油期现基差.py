#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC_原油期现基差.py
因子: SC_SPD_BASIS = 原油期现基差（元/桶）

公式: 现货价 - 期货主力合约收盘价

当前状态: [⛔永久跳过]
- L1: AKShare futures_spot_price(date, vars_list=['SC']) — 不支持SC品种
- L2: 手动计算需要原油现货价，无免费日频现货价源
- 不写占位符，不做L4回补

备注: AKShare futures_spot_price 不支持SC（原油）品种，
国内原油现货价格无免费日频数据源（隆众/普氏付费）。
国际原油（WTI/Brent）可通过 futures_foreign_hist 获取，
但与INE原油期货价格单位/标的不一致，无法直接计算基差。
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates

FCODE = "SC_SPD_BASIS"
SYM = "SC"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: AKShare futures_spot_price 不支持SC品种，原油现货价无免费日频源")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
