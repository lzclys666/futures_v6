#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
焦化厂炼焦煤库存
因子: JM_INV_COKING_PLANT = 焦化厂炼焦煤库存

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
"""JM_INV_COKING_PLANT - 焦化厂炼焦煤库存"""

import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

FACTOR_CODE = "JM_INV_COKING_PLANT"
SYMBOL = "JM"

def fetch_value():
    print("[L1-L3] 焦化厂炼焦煤库存需Mysteel订阅")
    print("[L4] DB历史回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        return val, 'db_回补', 0.5
    if '--manual' in sys.argv:
        try:
            v = float(input("请输入焦化厂炼焦煤库存(万吨): "))
            return v, '手动输入', 0.6
        except (ValueError, EOFError):
            pass
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("非交易日，跳过"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} ===")
    value, source, confidence = fetch_value()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[跳过] {FACTOR_CODE} 需付费数据")
