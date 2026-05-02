#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_期现基差.py
因子: AU_SPD_BASIS = 黄金期现基差（元/克）
      = SGE现货收盘价 - AU0期货收盘价

公式: AU_SPD_BASIS = AU_SPOT_SGE(晚盘价) - AU_FUT_CLOSE(收盘价)

当前状态: ✅正常
- 数据源: AKShare spot_golden_benchmark_sge() + futures_main_sina('AU0')，L1权威
- 采集逻辑: 现货晚盘价 - 期货收盘价
- obs_date: 取现货和期货日期中较新者
- bounds: [-100, 100]元/克（正常区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd

FACTOR_CODE = "AU_SPD_BASIS"
SYMBOL = "AU"
BOUNDS = (-100.0, 100.0)


def fetch():
    """L1: AKShare 沪金期货 + SGE现货基差"""
    print("[L1] AKShare futures_main_sina('AU0') + spot_golden_benchmark_sge()...")

    df_fut = ak.futures_main_sina(symbol="AU0")
    if df_fut is None or df_fut.empty:
        raise ValueError("AU0 futures empty")
    df_fut = df_fut.sort_values("日期")
    latest_fut = df_fut.iloc[-1]
    fut_price = float(latest_fut["收盘价"])
    fut_date = pd.to_datetime(latest_fut["日期"]).date()

    df_spot = ak.spot_golden_benchmark_sge()
    if df_spot is None or df_spot.empty:
        raise ValueError("SGE spot empty")
    df_spot = df_spot.sort_values("交易时间")
    latest_spot = df_spot.iloc[-1]
    spot_price = float(latest_spot["晚盘价"])
    spot_date = pd.to_datetime(latest_spot["交易时间"]).date()

    obs_date = max(fut_date, spot_date)
    raw_value = round(spot_price - fut_price, 2)
    print(f"[L1] spot={spot_price} CNY/g, fut={fut_price} CNY/g, basis={raw_value}")
    return raw_value, obs_date


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            print(f"[L4] 兜底: {val}")
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                       source="db_回补", source_confidence=0.5)
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source="akshare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
