#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EG_计算_期现基差.py
因子: EG_SPD_BASIS = 乙二醇期现基差

公式: 华东出罐价 - 期货结算价

当前状态: [⛔永久跳过]
- 华东出罐价需CCF（中纤网）付费订阅
- 无免费数据源

订阅优先级: ★★★（CCF年费）
替代付费源: CCF/隆众资讯
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import ensure_table, get_pit_dates

FACTOR_CODE = "EG_SPD_BASIS"
SYMBOL = "EG"

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FACTOR_CODE}: 华东出罐价需CCF付费订阅，无免费数据源")

if __name__ == "__main__":
    run()
