#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EG_抓取_煤制开工率.py
因子: EG_STK_COAL_RATE = 煤制乙二醇开工率

公式: 数据采集（无独立计算公式）

当前状态: [⛔永久跳过]
- 煤制开工率属商业数据，需隆众/CCF付费订阅
- 无免费数据源

订阅优先级: ★★★（隆众/CCF年费）
替代付费源: 隆众资讯/CCF
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import ensure_table, get_pit_dates

FACTOR_CODE = "EG_STK_COAL_RATE"
SYMBOL = "EG"

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print(f"[跳过] {FACTOR_CODE}: 煤制开工率需隆众/CCF付费订阅，无免费数据源")

if __name__ == "__main__":
    run()
