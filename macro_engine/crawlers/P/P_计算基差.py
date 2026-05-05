#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P_计算基差.py
因子: P_SPD_BASIS = 棕榈油期现基差（元/吨）

公式: P_SPD_BASIS = 棕榈油现货价 - 棕榈油期货收盘价

当前状态: [⛔永久跳过]
- AKShare futures_spot_price(vars_list=['P']) 只返回到2024-04-30的历史数据
- 无其他可靠免费源获取棕榈油现货价
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

订阅优先级: ★★★
替代付费源: MPOB官方月报 | SMM年费 | Mysteel年费（棕榈油现货）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import ensure_table, get_pit_dates, save_l4_fallback

FACTOR_CODE = "P_SPD_BASIS"
SYMBOL = "P"


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print("[⛔永久跳过] AKShare无当前棕榈油现货价格数据")
    print("[说明] 订阅MPOB月报/SMM/Mysteel后可手动录入")
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
