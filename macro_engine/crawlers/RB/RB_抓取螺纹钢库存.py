#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取螺纹钢库存
因子: RB_INV_STEEL = 抓取螺纹钢库存

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

import akshare as ak

FACTOR_CODE = "RB_INV_STEEL"
SYMBOL = "RB"

def fetch_inventory():
    # L1: AKShare 螺纹钢库存
    try:
        print("[L1] AKShare futures_inventory_em...")
        df = ak.futures_inventory_em(symbol="螺纹钢")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            inv_col = None
            for c in cols:
                if '库存' in str(c) or 'inventory' in str(c).lower():
                    inv_col = c; break
            if inv_col is None:
                inv_col = cols[-1]
            val = df.iloc[-1][inv_col]
            if isinstance(val, str):
                val = val.replace(',', '').strip()
            val = float(val)
            if 0 < val < 10000000:
                print(f"[L1] 成功: {val:.0f} 吨")
                return val, 'akshare', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: 我的钢铁网 API（备用）
    try:
        print("[L2] 我的钢铁网...")
        # TODO: 我的钢铁网螺纹钢库存API
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    # L4: DB回补
    print("[L4] DB历史回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] 兜底: {val}")
        return val, 'db_回补', 0.5
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("非交易日，跳过"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_inventory()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[失败] {FACTOR_CODE} 所有数据源均失败")
