#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取白银ETF持仓.py
因子: AG_DEM_ETF_HOLDING = 白银ETF持仓总量（吨）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- AKShare macro_cons_silver 返回白银ETF总库存（吨）
- 数据来源: 全球主要白银ETF汇总持仓

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

FACTOR_CODE = "AG_DEM_ETF_HOLDING"
SYMBOL = "AG"

def fetch():
    print("[L1] AKShare macro_cons_silver...")
    try:
        df = ak.macro_cons_silver()
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            val = float(row['总库存'])
            obs_date_str = str(row['日期'])[:10]
            print(f"[L1] 白银ETF持仓={val:.2f}吨 (obs={obs_date_str})")
            return val, obs_date_str
    except Exception as e:
        print(f"[L1] 失败: {e}")
    return None, None

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")
    val, data_date = fetch()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_macro_cons_silver")
        print(f"[OK] {FACTOR_CODE}={val:.2f} 写入成功")
    else:
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")

if __name__ == "__main__":
    main()
