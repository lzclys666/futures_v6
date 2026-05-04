#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AO_豆一期货收盘价.py
因子: AO_FUT_CLOSE = 大连豆一期货主力收盘价（元/吨）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_main_sina(symbol='AO0')，source_confidence=1.0
- L2: AKShare futures_zh_daily_sina(symbol='AO0')，source_confidence=0.9
- L3: save_l4_fallback() 兜底
- bounds: [2500, 6500]元/吨（豆一期货历史价格区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "AO_FUT_CLOSE"
SYMBOL = "AO"
BOUNDS = (2500, 6500)


def fetch():
    # L1: AKShare 豆一期货日行情（主力合约）
    print("[L1] AKShare futures_main_sina(symbol='AO0')...")
    df = ak.futures_main_sina(symbol="AO0")
    if df is None or df.empty:
        raise ValueError("no data")
    latest = df.sort_values("日期").iloc[-1]
    raw_value = float(latest["收盘价"])
    obs_date = pd.to_datetime(latest["日期"]).date()
    return raw_value, obs_date


def fetch_l2():
    # L2: AKShare 备用（次选合约）
    print("[L2] AKShare futures_zh_daily_sina(symbol='AO0')...")
    df = ak.futures_zh_daily_sina(symbol="AO0")
    if df is None or df.empty:
        raise ValueError("no data")
    latest = df.sort_values("date").iloc[-1]
    raw_value = float(latest["close"])
    obs_date = pd.to_datetime(latest["date"]).date()
    return raw_value, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    raw_value, data_obs_date = None, None

    # L1
    try:
        raw_value, data_obs_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2
    if raw_value is None:
        try:
            raw_value, data_obs_date = fetch_l2()
        except Exception as e:
            print(f"[L2] 失败: {e}")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(豆一收盘价)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
            print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
        return

    # bounds校验
    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(豆一收盘价)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="akshare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={data_obs_date}")


if __name__ == "__main__":
    main()
