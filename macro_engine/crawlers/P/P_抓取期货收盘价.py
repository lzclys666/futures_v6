#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取期货收盘价
因子: P_FUT_CLOSE = 抓取期货收盘价

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date
import pandas as pd

FACTOR_CODE = "P_FUT_CLOSE"
SYMBOL = "P"
EXPECTED_MIN = 5000
EXPECTED_MAX = 15000

def fetch():
    df = ak.futures_main_sina(symbol="P0")
    if df.empty:
        raise ValueError("AKShare无P0数据")
    latest = df.sort_values('\u65e5\u671f').iloc[-1]
    raw_value = float(latest['\u6536\u76d8\u4ef7'])
    obs_date = pd.to_datetime(latest['\u65e5\u671f']).date()
    return raw_value, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1] %s: %s" % (FACTOR_CODE, e))
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print("[L4FB] %s=%.1f" % (FACTOR_CODE, latest))
            return
        print("[SKIP] %s: no data" % FACTOR_CODE)
        return

    if not (EXPECTED_MIN <= raw_value <= EXPECTED_MAX):
        print("[WARN] %s=%.1f out of [%d,%d]" % (FACTOR_CODE, raw_value, EXPECTED_MIN, EXPECTED_MAX))
        return

    pub_date = date.today()
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
    print("[OK] %s=%.1f obs=%s" % (FACTOR_CODE, raw_value, obs_date))

if __name__ == "__main__":
    main()
