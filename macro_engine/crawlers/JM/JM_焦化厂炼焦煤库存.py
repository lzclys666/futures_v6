#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
焦化厂炼焦煤库存
因子: JM_INV_COKING_PLANT = 焦化厂炼焦煤库存

公式: 数据采集（无独立计算公式）

当前状态: [WARN] 待修复
- 补充 L1-L3 框架代码
- 尝试过的数据源及结果：需补充

订阅优先级: [付费-Mysteel]
替代付费源: Mysteel(年费)
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

FACTOR_CODE = "JM_INV_COKING_PLANT"
SYMBOL = "JM"
# 付费来源: Mysteel(年费)

def fetch_value():
    """四层漏斗获取焦化厂炼焦煤库存"""
    # L1: 免费权威源
    try:
        print("[L1] 尝试免费权威源...")
        # 暂无可靠免费数据源
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: 免费聚合源
    try:
        print("[L2] 尝试免费聚合源...")
        # 暂无可用免费聚合数据
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    # L3: 付费源（需订阅）
    try:
        print("[L3] 付费源（需订阅）...")
        print("[L3] Mysteel - 年费订阅，数据需人工订阅获取")
    except Exception as e:
        print(f"[L3] 失败: {e}")
    
    # L4: DB兜底
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
