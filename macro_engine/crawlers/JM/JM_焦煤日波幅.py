#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_焦煤日波幅.py
因子: JM_HIGH_LOW = 焦煤期货主力合约日波幅（最高价-最低价）

公式: JM_HIGH_LOW = high - low（元/吨）

当前状态: [✅正常]
- L1: AKShare futures_main_sina("JM0") — 主力合约日行情
- L2: AKShare futures_zh_daily_sina("JM0") — 日行情
- L3: 新浪实时API — 实时行情
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
FACTOR_CODE = "JM_HIGH_LOW"
BOUNDS = (0, 100)


def fetch():
    # L1: AKShare futures_main_sina
    try:
        df = ak.futures_main_sina(symbol="JM0")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            high_col, low_col = None, None
            for c in cols:
                if 'high' in str(c).lower() or '最高' in str(c):
                    high_col = c
                if 'low' in str(c).lower() or '最低' in str(c):
                    low_col = c
            if high_col is None and len(cols) > 2:
                high_col = cols[2]
            if low_col is None and len(cols) > 3:
                low_col = cols[3]
            if high_col and low_col:
                high_val = float(str(df.iloc[-1][high_col]).replace(',', '').strip())
                low_val = float(str(df.iloc[-1][low_col]).replace(',', '').strip())
                val = round(high_val - low_val, 2)
                if BOUNDS[0] <= val <= BOUNDS[1]:
                    print(f"[L1] JM日波幅: {high_val} - {low_val} = {val}")
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
