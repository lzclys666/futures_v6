#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取持仓排名
因子: NR_POS_NET = 抓取持仓排名

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
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
import pandas as pd
from datetime import timedelta

FACTOR_CODE = "NR_POS_NET"
SYMBOL = "NR"
MIN_VALUE = -50000
MAX_VALUE = 100000


def fetch_net(date_str):
    try:
        result = ak.get_shfe_rank_table(date=date_str, vars_list=['NR'])
        if isinstance(result, dict) and result:
            main_contract = list(result.keys())[0]
            df = result[main_contract]
            df['long_open_interest'] = pd.to_numeric(df['long_open_interest'], errors='coerce')
            df['short_open_interest'] = pd.to_numeric(df['short_open_interest'], errors='coerce')
            long5 = df['long_open_interest'].head(5).sum()
            short5 = df['short_open_interest'].head(5).sum()
            return long5 - short5
    except Exception:
        return None


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
    print(f"=== NR持仓排名 === obs={obs_date}")

    value = None
    obs_str = obs_date.strftime('%Y%m%d')

    # L1: 当前日期
    net = fetch_net(obs_str)
    if net is not None and MIN_VALUE <= net <= MAX_VALUE:
        value = float(net)
        print(f"[L1] NR净多头={net:.0f}手")

    # L2: 回退
    if value is None:
        for delta in range(1, 5):
            prev = (obs_date - timedelta(days=delta)).strftime('%Y%m%d')
            net = fetch_net(prev)
            if net is not None and MIN_VALUE <= net <= MAX_VALUE:
                value = float(net)
                print(f"[L1] NR净多头={net:.0f}手 (日期={prev})")
                break

    # L3: DB兜底
    if value is None:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            value = val
            print(f"[L3] DB兜底: {value}")

    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=1.0)
        print(f"OK: NR_POS_NET={value:.0f}")
    else:
        print("FAIL: NR持仓排名无数据")
        exit(1)


if __name__ == "__main__":
    main()
