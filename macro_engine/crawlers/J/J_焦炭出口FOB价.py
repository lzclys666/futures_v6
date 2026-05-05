#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭出口FOB价.py
因子: J_FOB_EXPORT = 焦炭出口FOB价

公式: J_FOB_EXPORT = 焦炭出口FOB价（美元/吨）

当前状态: [⛔永久跳过]
- L1: 无免费数据源
- L2: 无备源
- L3: 付费订阅: 隆众/普氏（年费）
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import get_pit_dates

def main():
    pub_date, obs_date = get_pit_dates()
    print(f"[跳过] J_FOB_EXPORT: 无免费数据源（付费订阅: 隆众/普氏）")

if __name__ == "__main__":
    main()
