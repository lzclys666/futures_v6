#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BR_批次2手动因子.py
因子: BR_SUP_RATE/BR_DEM_AUTO/BR_DEM_TIRE_ALLST/BR_DEM_TIRE_SEMI

公式: 数据采集（无独立计算公式）

当前状态: [⚠️待修复]
- L1: 无免费源（付费订阅: 隆众资讯/中国汽车工业协会）
- L2: 无备选源
- L3: save_l4_fallback() 兜底（仅当db有历史值时写入）

订阅优先级: ★★★
替代付费源: SMM(年费)/隆众资讯(年费)/中国汽车工业协会
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_l4_fallback, get_pit_dates

SYMBOL = "BR"


def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === BR批次2因子 === obs={obs_date}")
    print("[L1-L2] 无免费数据源")

    for fc in ['BR_SUP_RATE', 'BR_DEM_AUTO', 'BR_DEM_TIRE_ALLSTEEL', 'BR_DEM_TIRE_SEMI']:
        if not save_l4_fallback(fc, SYMBOL, pub_date, obs_date,
                                 extra_msg="(批次2付费因子)"):
            print(f"[WARN] {fc} DB无历史值，需手动录入")


if __name__ == "__main__":
    main()
