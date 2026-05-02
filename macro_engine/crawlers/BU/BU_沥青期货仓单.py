#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沥青期货仓单
因子: BU_BU_STK_WARRANT = 沥青期货仓单

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

FACTOR_CODE = "BU_BU_STK_WARRANT"
SYMBOL = "BU"

def fetch_shfe_receipt(obs_date):
    date_str = obs_date.strftime("%Y%m%d")
    
    try:
        print(f"[L1] AKShare futures_shfe_warehouse_receipt date={date_str}...")
        result = ak.futures_shfe_warehouse_receipt(date=date_str)
        if result is not None:
            if isinstance(result, dict):
                for k, v in result.items():
                    if isinstance(v, pd.DataFrame) and len(v) > 0:
                        df = v
                        break
                else:
                    df = None
            elif isinstance(result, pd.DataFrame):
                df = result
            else:
                df = None
            
            if df is not None and len(df) > 0:
                cols = df.columns.tolist()
                bu_col = None
                for c in cols:
                    c_str = str(c).lower()
                    if 'bu' in c_str or '沥青' in c_str or '石油' in c_str:
                        bu_col = c; break
                if bu_col is None:
                    for c in cols:
                        if df[c].dtype in ['float64', 'int64']:
                            bu_col = c; break
                    if bu_col is None:
                        bu_col = cols[-1]
                val = float(df[bu_col].iloc[-1])
                if 0 <= val <= 5000000:
                    print(f"[L1] Receipt: {val:.0f} tons")
                    return val, 'akshare_futures_shfe_warehouse_receipt', 1.0
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
    value, source, confidence = fetch_shfe_receipt(obs_date)
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[FAIL] {FACTOR_CODE} all sources failed")
