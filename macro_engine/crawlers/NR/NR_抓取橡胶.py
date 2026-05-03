#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取橡胶
因子: NR_INV_TOTAL = 抓取橡胶

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
from db_utils import ensure_table, save_to_db, get_latest_value, get_pit_dates
import akshare as ak
import pandas as pd
from datetime import date

FACTOR_CODE = "NR_INV_TOTAL"
SYMBOL = "NR"
EXPECTED_MIN = 10000
EXPECTED_MAX = 100000

def fetch():
    df = ak.futures_inventory_em(symbol="nr")
    df['date'] = pd.to_datetime(df['日期']).dt.date
    latest = df.sort_values('date').iloc[-1]
    raw_value = float(latest['库存'])
    obs_date = latest['date']
    return raw_value, obs_date

def main():
    # 交易日检查
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print(f"[SKIP] 非交易日")
        return

    try:
        raw_value, data_obs_date = fetch()
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print(f"[L4] {FACTOR_CODE}={latest:.2f} 回补成功")
            return
        print(f"[SKIP] {FACTOR_CODE}: no data")
        return

    if not (EXPECTED_MIN <= raw_value <= EXPECTED_MAX):
        print(f"[WARN] {FACTOR_CODE}={raw_value:.1f} out of [{EXPECTED_MIN},{EXPECTED_MAX}]")
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value, source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value:.1f} obs={data_obs_date}")

if __name__ == "__main__":
    main()
