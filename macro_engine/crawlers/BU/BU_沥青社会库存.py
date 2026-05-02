#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沥青社会库存
因子: BU_BU_STK_SOCIAL = 沥青社会库存

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
import pandas as pd

FACTOR_CODE = "BU_BU_STK_SOCIAL"
SYMBOL = "BU"

def fetch_bu_inventory():
    try:
        print("[L1] AKShare futures_inventory_em(symbol='bu')...")
        df = ak.futures_inventory_em(symbol='bu')
        if df is not None and len(df) > 0:
            df.columns = ['date', 'stat', 'change']
            df['date'] = pd.to_datetime(df['date'])
            latest = df.iloc[-1]
            val = float(latest['stat'])
            actual_date = latest['date'].date()
            print(f"[L1] BU port inventory({actual_date}): {val:.0f}")
            return val, actual_date, 'akshare_futures_inventory_em(alternative)', 0.8
    except Exception as e:
        print(f"[L1] Failed: {e}")
    
    print("[L4] DB history fallback...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] Fallback: {val}")
        return val, None, 'db_fallback', 0.5
    return None, None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, actual_date, source, confidence = fetch_bu_inventory()
    if value is not None:
        write_date = actual_date if actual_date else obs_date
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, write_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[FAIL] {FACTOR_CODE} all sources failed")
