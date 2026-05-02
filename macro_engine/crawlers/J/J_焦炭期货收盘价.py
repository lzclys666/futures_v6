#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
焦炭期货收盘价
因子: J_J_FUT_CLOSE = 焦炭期货收盘价

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

FACTOR_CODE = "J_J_FUT_CLOSE"
SYMBOL = "J"

def fetch_j_close(obs_date):
    try:
        df = ak.futures_main_sina(symbol='J0')
        if df is not None and len(df) > 0:
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'oi', 'settle']
            df['date'] = pd.to_datetime(df['date'])
            mask = df['date'] <= pd.Timestamp(obs_date)
            if mask.sum() == 0:
                row = df.iloc[-1]
            else:
                row = df[mask].iloc[-1]
            
            close = row.get('close') or row.get('settle')
            if close is not None and not pd.isna(close):
                close = float(close)
                actual_date = row['date'].date()
                print(f"[L1] J0 settle({actual_date}): {close}")
                return close, actual_date, 'akshare_futures_main_sina', 1.0
    except Exception as e:
        print(f"[L1] J0 failed: {e}")
    
    print("[L4] DB history fallback...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] Fallback: {val}")
        return val, obs_date, 'db_fallback', 0.5
    return None, None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, actual_date, source, confidence = fetch_j_close(obs_date)
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[FAIL] {FACTOR_CODE} all sources failed")
