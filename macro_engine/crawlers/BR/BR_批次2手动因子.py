#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批次2手动因子
因子: 待定义 = 批次2手动因子

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
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
            print(f"✅ {fc}={v} L4回补成功")
        else:
            print(f"⚠️  {fc} 无历史数据")

if __name__ == "__main__":
    main()
