#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取净持仓.py
因子: AG_POS_NET = 白银期货持仓量（手）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- AKShare futures_main_sina(symbol='AG0') 获取白银期货AG0持仓量（手）
- 注意：AG_POS_NET同时由AG_抓取期货日行情.py写入，存在重复写入
- 两者数据源相同（均为新浪AG0），重复写入无害

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

FACTOR_CODE = "AG_POS_NET"
SYMBOL = "AG"

def fetch():
    print("[L1] AKShare futures_main_sina AG0...")
    df = ak.futures_main_sina(symbol="AG0")
    if df is None or len(df) == 0:
        return None
    col_map = {str(c).strip(): c for c in df.columns}
    if "持仓量" in col_map:
        val = float(df.iloc[-1][col_map["持仓量"]])
        print(f"[L1] AG持仓量={val}")
        return val
    return None

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")
    val = fetch()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_main_sina")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")

if __name__ == "__main__":
    main()
