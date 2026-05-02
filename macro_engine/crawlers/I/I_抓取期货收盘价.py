#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取期货收盘价
因子: I_FUT_MAIN = 抓取期货收盘价

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date

FACTOR_CODE = "I_FUT_MAIN"
SYMBOL = "I"
EXPECTED_MIN = 500
EXPECTED_MAX = 1200

def fetch():
    df = ak.futures_main_sina(symbol="i0")
    df['日期'] = pd.to_datetime(df['日期']).dt.date
    latest = df.sort_values('日期').iloc[-1]
    raw_value = float(latest['收盘价'])
    obs_date = latest['日期']
    return raw_value, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print(f"[L4 Fallback] {FACTOR_CODE}={latest}")
            return
        print(f"[L4 SKIP] {FACTOR_CODE}: no data")
        return

    if not (EXPECTED_MIN <= raw_value <= EXPECTED_MAX):
        print(f"[WARN] {FACTOR_CODE}={raw_value} out of [{EXPECTED_MIN},{EXPECTED_MAX}]")
        return

    pub_date = date.today()
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")

if __name__ == "__main__":
    import pandas as pd
    main()
