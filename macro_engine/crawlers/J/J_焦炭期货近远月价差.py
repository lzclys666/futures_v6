#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
焦炭期货近远月价差
因子: J_J_SPD_NEAR_FAR = 焦炭期货近远月价差

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

FACTOR_CODE = "J_J_SPD_NEAR_FAR"
SYMBOL = "J"

def fetch_near_far_spread(obs_date):
    def get_settle(symbol):
        try:
            df = ak.futures_main_sina(symbol=symbol)
            if df is not None and len(df) > 0:
                df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'oi', 'settle']
                df['date'] = pd.to_datetime(df['date'])
                mask = df['date'] <= pd.Timestamp(obs_date)
                row = df[mask].iloc[-1] if mask.sum() > 0 else df.iloc[-1]
                return float(row.get('close') or row.get('settle') or 0)
        except:
            return None
    
    j0 = get_settle('J0')
    j1 = get_settle('J1')
    
    if j0 is not None and j1 is not None:
        spread = j0 - j1
        print(f"[L1] J near-far spread: {spread:.2f} (J0={j0:.1f}, J1={j1:.1f})")
        return spread, 'derived(J0-J1)', 0.9
    
    print(f"[WARN] J0={j0}, J1={j1}")
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_near_far_spread(obs_date)
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source='db_fallback')
            print(f"[OK] {FACTOR_CODE}={val} L4 fallback OK")
        else:
            print(f"[FAIL] {FACTOR_CODE} all sources failed")
