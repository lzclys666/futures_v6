#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算RU-NR价差
因子: NR_SPD_RU_NR = 计算RU-NR价差

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
from datetime import date, timedelta

FACTOR_CODE = "NR_SPD_RU_NR"
SYMBOL = "NR"
EXPECTED_MIN = 0.7
EXPECTED_MAX = 1.3

def fetch():
    # L1: 用今日或最近交易日的主力合约收盘价
    nr_df = ak.futures_main_sina(symbol="NR0")
    ru_df = ak.futures_main_sina(symbol="RU0")
    if nr_df.empty or ru_df.empty:
        raise ValueError("AKShare无数据")
    
    nr_latest = nr_df.sort_values('\u65e5\u671f').iloc[-1]
    ru_latest = ru_df.sort_values('\u65e5\u671f').iloc[-1]
    nr_price = float(nr_latest['\u6536\u76d8\u4ef7'])
    ru_price = float(ru_latest['\u6536\u76d8\u4ef7'])
    obs_date = pd.to_datetime(nr_latest['\u65e5\u671f']).date()
    ratio = round(nr_price / ru_price, 4)
    return ratio, obs_date

def main():
    import pandas as pd
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1] %s: %s" % (FACTOR_CODE, e))
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print("[L4FB] %s=%.4f" % (FACTOR_CODE, latest))
            return
        print("[SKIP] %s: no data" % FACTOR_CODE)
        return

    if not (EXPECTED_MIN <= raw_value <= EXPECTED_MAX):
        print("[WARN] %s=%.4f out of [%.1f,%.1f]" % (FACTOR_CODE, raw_value, EXPECTED_MIN, EXPECTED_MAX))
        return

    pub_date = date.today()
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
    print("[OK] %s=%.4f obs=%s" % (FACTOR_CODE, raw_value, obs_date))

if __name__ == "__main__":
    import pandas as pd
    main()
