#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钢厂焦炭可用天数
因子: J_J_STK_STEEL_DAYS = 钢厂焦炭可用天数

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

FACTOR_CODE = "J_J_STK_STEEL_DAYS"
SYMBOL = "J"

def fetch_steel_days():
    print("[NOTE] Sample steel mill coke inventory days needs Mysteel paid account")
    print("[L4] DB history fallback...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] Fallback: {val}")
        return val, 'db_fallback', 0.5
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_steel_days()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[SKIP] {FACTOR_CODE} no history to fall back to")
