#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取期货持仓
因子: NR_FUT_OI = 抓取期货持仓

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
from datetime import timedelta

FACTOR_CODE = "NR_FUT_OI"
SYMBOL = "NR"
MIN_VALUE = 10000
MAX_VALUE = 200000


def main():
    pub_date, obs_date = get_pit_dates(freq="日频")
    if obs_date is None:
        from datetime import date
        obs_date = date.today()
        for d in range(1, 10):
            check = obs_date - timedelta(days=d)
            if check.weekday() < 5:
                obs_date = check
                break
        pub_date = obs_date

    ensure_table()
    print(f"=== NR期货持仓 === obs={obs_date}")

    value = None

    # L1: NR期货持仓量
    try:
        df = ak.futures_main_sina(symbol='NR0')
        if df is not None and not df.empty:
            latest = df.sort_values('日期').iloc[-1]
            oi = float(latest['持仓量'])
            price = float(latest['收盘价'])
            if MIN_VALUE <= oi <= MAX_VALUE:
                value = oi
                print(f"[L1] NR持仓量={oi:.0f}手, 收盘={price}")
    except Exception as e:
        print(f"[L1] NR持仓量失败: {e}")

    # L2: DB兜底
    if value is None:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            value = val
            print(f"[L2] DB兜底: {value}")

    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=1.0, source="akshare_futures_main_sina")
        print(f"OK: NR_FUT_OI={value:.0f}")
    else:
        print("FAIL: NR持仓量无数据")
        exit(1)


if __name__ == "__main__":
    main()
