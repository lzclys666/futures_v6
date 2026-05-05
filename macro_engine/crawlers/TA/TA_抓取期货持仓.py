#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取期货持仓
因子: TA_POS_OI = 抓取期货持仓

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "TA_POS_OI"
SYMBOL = "TA"
MIN_VALUE = 100000
MAX_VALUE = 2000000


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true')
    args = parser.parse_args()

    ensure_table()
    pub_date, obs_date = get_pit_dates(freq='日频')
    if obs_date is None:
        print("FAIL: 无有效交易日")
        exit(1)

    print(f"=== PTA期货持仓量 === obs={obs_date}")
    value = None
    source_conf = 1.0

    # L1: futures_main_sina TA0 持仓量
    try:
        df = ak.futures_main_sina(symbol='TA0')
        df = df.sort_values('日期')
        # 找最近 <= obs_date 的记录
        df['日期_dt'] = pd.to_datetime(df['日期'])
        mask = df['日期_dt'] <= pd.Timestamp(obs_date)
        if mask.any():
            row = df[mask].iloc[-1]
            value = float(row['持仓量'])
            print(f"[L1] TA0持仓量={value:.0f}手 日期={row['日期']}")
        else:
            print(f"[L1] 无obs_date={obs_date}的数据")
    except Exception as e:
        print(f"[L1] TA0持仓量失败: {e}")

    # L2: 兜底历史值
    if value is None:
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

    if value is not None and MIN_VALUE <= value <= MAX_VALUE:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=source_conf)
        print(f"OK: TA_POS_OI={value:.0f}")
        return 0
    else:
        print(f"FAIL: TA_POS_OI={value} 超出合理范围[{MIN_VALUE},{MAX_VALUE}]")
        return 1


if __name__ == '__main__':
    exit(main())
