#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB_SMM沪铅现货价格.py
因子: PB_SPT_SMM = SMM铅现货报价（元/吨）
当前状态: [⛔永久跳过]
- 原因: 付费订阅（SMM），无免费数据源
- 尝试: AKShare无SMM铅现货接口
- 解决方案: 订阅SMM后手动录入
- 不写占位符，不做L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback

FCODE = "PB_PB_SPT_SMM"
SYM = "PB"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FCODE} = None (obs={obs_date})")
    print(f"  原因: 付费订阅(SMM)，无免费数据源")
    print(f"  不写占位符，不做L4回补")


if __name__ == "__main__":
    main()
