#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P_计算基差.py
因子: P_SPD_BASIS = 棕榈油期现基差（元/吨）

公式: P_SPD_BASIS = 棕榈油现货价 - 棕榈油期货收盘价

当前状态: ⛔永久跳过
- AKShare futures_spot_price(vars_list=['P']) 只返回到2024-04-30的历史数据，无当前数据
- 无其他可靠免费源获取棕榈油现货价
- 不写占位符（obs_date=2024-04-30的数据无参考价值）

订阅优先级: ★★★
替代付费源: MPOB官方月报 | SMM年费 | Mysteel年费（棕榈油现货）
"""
import sys, os
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date
import pandas as pd

FACTOR_CODE = "P_SPD_BASIS"
SYMBOL = "P"

def main():
    print("[SKIP] P_SPD_BASIS: AKShare只返回到2024-04-30的历史数据，无当前免费源")
    print("[SKIP] 订阅MPOB月报/SMM/Mysteel后，手动录入棕榈油现货价再计算基差")
    print("[SKIP] 不写占位符")

if __name__ == "__main__":
    main()
