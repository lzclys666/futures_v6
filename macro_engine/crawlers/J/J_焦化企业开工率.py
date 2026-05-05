#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦化企业开工率.py
因子: J_STK_COKE_RATE = 焦化企业开工率

公式: J_STK_COKE_RATE = 焦化企业开工率（%）

当前状态: [⛔永久跳过]
- 无免费数据源（付费订阅: Mysteel/汾渭）
- 不写占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import get_pit_dates

def main():
    pub_date, obs_date = get_pit_dates()
    print(f"[跳过] J_STK_COKE_RATE: 无免费数据源（付费订阅: Mysteel/汾渭）")

if __name__ == "__main__":
    main()
