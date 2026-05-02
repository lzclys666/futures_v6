#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美元兑人民币汇率
因子: BU_BU_FX_USDCNY = 美元兑人民币汇率

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

FACTOR_CODE = "BU_BU_FX_USDCNY"
SYMBOL = "BU"

def fetch_usdcny():
    try:
        print("[L1] AKShare fx_spot_quote...")
        df = ak.fx_spot_quote()
        if df is not None and len(df) > 0:
            df.columns = ['pair', 'bid', 'ask']
            usd_row = df[df['pair'].astype(str).str.contains('USD')]
            if len(usd_row) > 0:
                row = usd_row.iloc[-1]
                bid = float(row['bid'])
                ask = float(row['ask'])
                mid = (bid + ask) / 2
                print(f"[L1] USD/CNY: bid={bid} ask={ask} mid={mid}")
                return mid, 'akshare_fx_spot_quote', 1.0
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
    value, source, confidence = fetch_usdcny()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[FAIL] {FACTOR_CODE} all sources failed")
