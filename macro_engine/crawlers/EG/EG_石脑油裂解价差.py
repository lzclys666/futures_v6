#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EG_计算_石脑油裂解价差.py
因子: EG_SPT_NAPTHA = 石脑油裂解价差

公式: 乙二醇价格 - 石脑油价格

当前状态: [⛔永久跳过]
- 石脑油价格需隆众/普氏付费订阅
- 无免费数据源

订阅优先级: ★★★（普氏/隆众年费）
替代付费源: 普氏能源/隆众资讯
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import ensure_table, get_pit_dates

FACTOR_CODE = "EG_SPT_NAPTHA"
SYMBOL = "EG"

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FACTOR_CODE}: 石脑油价格需普氏/隆众付费订阅，无免费数据源")

if __name__ == "__main__":
    run()
