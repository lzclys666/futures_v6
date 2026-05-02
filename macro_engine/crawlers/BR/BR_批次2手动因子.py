#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次2手动因子
因子: 批次2手动因子 = BR_SUP_RATE/BR_DEM_AUTO/BR_DEM_TIRE_ALLST/BR_DEM_TIRE_SEMI

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 数据源: 无免费源，仅L4回补（手动录入数据回填）
- 采集逻辑: L4回补，仅当db有历史值时写入
- bounds: 因因子而异

订阅优先级: ★★★
替代付费源: SMM(年费)/隆众资讯(年费)/中国汽车工业协会
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

SYMBOL = "BR"

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === BR批次2因子 === obs={obs_date}")
    print("[L1-L3] 无免费数据源")
    for fc in ['BR_SUP_RATE', 'BR_DEM_AUTO', 'BR_DEM_TIRE_ALLSTEEL', 'BR_DEM_TIRE_SEMI']:
        v = get_latest_value(fc, SYMBOL)
        if v is not None:
            save_to_db(fc, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {fc}={v} L4回补成功")
        else:
            print(f"[WARN] {fc} 无历史数据")

if __name__ == "__main__":
    main()
