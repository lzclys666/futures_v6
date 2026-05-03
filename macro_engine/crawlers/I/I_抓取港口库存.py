#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取港口库存
因子: I_STK_PORT = 抓取港口库存

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

FACTOR_CODE = "I_STK_PORT"
SYMBOL = "I"
EXPECTED_MIN = 0
EXPECTED_MAX = 6000  # 万吨

def fetch():
    df = ak.futures_inventory_em(symbol="\u94c1\u77ff\u77f3")
    df['\u65e5\u671f'] = df['\u65e5\u671f'].apply(
        lambda x: pd.to_datetime(str(x)).date() if pd.notna(x) else None
    )
    latest = df.sort_values('\u65e5\u671f').iloc[-1]
    raw_value = float(latest['\u5e93\u5b58'])  # 单位: 万吨
    obs_date = latest['\u65e5\u671f']
    return raw_value, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1 FAIL] %s: %s" % (FACTOR_CODE, e))
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print("[L4 Fallback] %s=%.2f" % (FACTOR_CODE, latest))
            return
        print("[L4 SKIP] %s: no data" % FACTOR_CODE)
        return

    if not (EXPECTED_MIN <= raw_value <= EXPECTED_MAX):
        print("[WARN] %s=%.1f out of [%d,%d]" % (FACTOR_CODE, raw_value, EXPECTED_MIN, EXPECTED_MAX))
        return

    pub_date = date.today()
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
    print("[OK] %s=%.1f obs=%s" % (FACTOR_CODE, raw_value, obs_date))

if __name__ == "__main__":
    import pandas as pd
    main()
