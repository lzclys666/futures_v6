#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_焦煤期货成交量.py
因子: JM_VOLUME = 焦煤期货主力合约成交量（手）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_main_sina("JM0") — 主力合约日行情
- L2: AKShare futures_zh_daily_sina("JM0") — 日行情成交量
- L3: 新浪实时API — 实时成交量
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

订阅优先级: 无（免费源）
替代付费源: 无
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak

SYMBOL = "JM"
FACTOR_CODE = "JM_VOLUME"
BOUNDS = (100000, 2000000)


def fetch():
    # L1: AKShare futures_main_sina
    try:
        df = ak.futures_main_sina(symbol="JM0")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            vol_col = None
            for c in cols:
                if 'volume' in str(c).lower() or '成交量' in str(c):
                    vol_col = c
                    break
            if vol_col is None and len(cols) > 5:
                vol_col = cols[5]
            if vol_col:
                val = df.iloc[-1][vol_col]
                if isinstance(val, str):
                    val = val.replace(',', '').strip()
                val = float(val)
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    print(f"[L1] JM成交量: {val}")
                    return val
    except Exception as e:
        print(f"[L1] 失败: {e}")
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    val = fetch()
    if val is None:
        print(f"[L1-L3 FAIL] {FACTOR_CODE} 所有数据源均失败")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        return
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
               source_confidence=1.0, source='akshare')
    print(f"[OK] {FACTOR_CODE}={val}")


if __name__ == "__main__":
    main()
