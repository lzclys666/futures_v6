#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BR_抓取仓单.py
因子: BR_STK_WARRANT = 丁二烯橡胶仓单（吨）

公式: 数据采集（无独立计算公式）

当前状态: [⚠️待修复]
- L1: AKShare futures_inventory_em(symbol='丁二烯橡胶')，source_confidence=1.0
- L2: 无备选源（丁二烯橡胶仓单仅有东方财富聚合，无直接免费API）
- L3: save_l4_fallback() 兜底
- ⚠️ 已知问题: 该API返回的"库存"列实为总库存（与BR_INV_TOTAL同源），
  非严格意义上的交易所注册仓单。待找到独立仓单数据源后修复。
  当前两个因子数值相同，使用时需注意。
- bounds: [0, 50000]吨（丁二烯橡胶仓单合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "BR_STK_WARRANT"
SYMBOL = "BR"
BOUNDS = (0.0, 50000.0)


def fetch():
    """L1: AKShare 丁二烯橡胶仓单（与库存同接口）"""
    print("[L1] AKShare futures_inventory_em(symbol='丁二烯橡胶')...")
    df = ak.futures_inventory_em(symbol="丁二烯橡胶")
    if df is None or df.empty:
        raise ValueError("no data")
    latest = df.sort_values("日期").iloc[-1]
    raw_value = float(latest["库存"])
    obs_date = pd.to_datetime(latest["日期"]).date()
    return raw_value, obs_date


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    raw_value, data_obs_date = None, None

    # L1
    try:
        raw_value, data_obs_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源
    if raw_value is None:
        print("[L2] 无备选源（丁二烯橡胶仓单仅有东方财富聚合，无直接免费API）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(BR仓单)"):
            pass
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(BR仓单)"):
            pass
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="akshare_futures_inventory_em", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={data_obs_date}")
