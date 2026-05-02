#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
焦炭期货仓单
因子: J_J_STK_WARRANT = 焦炭期货仓单

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

FACTOR_CODE = "J_J_STK_WARRANT"
SYMBOL = "J"

def fetch_dce_receipt(obs_date):
    date_str = obs_date.strftime("%Y%m%d")
    
    try:
        print(f"[L1] AKShare futures_warehouse_receipt_dce date={date_str}...")
        df = ak.futures_warehouse_receipt_dce(date=date_str)
        if df is not None and len(df) > 0:
            print(f"[L1] DCE receipt data: {df.shape}")
            cols = df.columns.tolist()
            for idx, row in df.iterrows():
                row_str = str(row.values)
                if 'J' in row_str or '焦炭' in row_str:
                    for val in row.values:
                        if isinstance(val, (int, float)) and not pd.isna(val):
                            print(f"[L1] J receipt: {val:.0f}")
                            return float(val), 'akshare_futures_warehouse_receipt_dce', 1.0
    except Exception as e:
        print(f"[L1] Failed: {e}")
    
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
    value, source, confidence = fetch_dce_receipt(obs_date)
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[FAIL] {FACTOR_CODE} all sources failed")
