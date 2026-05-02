#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青期现基差.py
因子: BU_BU_SPD_BASIS = 沥青期现基差（元/吨）= 华东现货价 - BU0期货结算价

公式: BU_BU_SPD_BASIS = BU_BU_SPT_EAST_CHINA - BU0动态结算价

当前状态: ✅正常
- 数据源: AKShare futures_spot_price(vars_list=['BU']) + futures_main_sina('BU0')，L1权威
- 采集逻辑: BU取最近5个工作日现货价，基差由现货-期货结算价计算
- obs_date: 数据实际日期
- bounds: [-500, 1000]元/吨（沥青期现基差合理区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd
from datetime import timedelta

FACTOR_CODE = "BU_BU_SPD_BASIS"
SYMBOL = "BU"
BOUNDS = (-500.0, 1000.0)


def fetch_spot(obs_date):
    """L1: AKShare 沥青现货价（尝试最近5个工作日）"""
    print("[L1] AKShare futures_spot_price(vars_list=['BU'])...")
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime("%Y%m%d")
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=["BU"])
            if df is None or df.empty:
                continue
            row = df.sort_values("date").iloc[-1]
            spot = float(row["spot_price"])
            if spot <= 0:
                continue
            actual_date = pd.to_datetime(row["date"]).date()
            print(f"[L1] 现货价={spot} (date={date_str})")
            return spot, actual_date
        except Exception as e:
            print(f"[L1] {date_str}: {e}")
    return None, None


def fetch_fut_settle(obs_date):
    """L1: AKShare BU0期货结算价"""
    print("[L1] AKShare futures_main_sina(symbol='BU0')...")
    try:
        df = ak.futures_main_sina(symbol="BU0")
        if df is None or df.empty:
            raise ValueError("empty")
        latest = df.sort_values("日期").iloc[-1]
        settle = float(latest.get("动态结算价") or latest.get("收盘价") or 0)
        if settle <= 0:
            raise ValueError(f"结算价<=0: {settle}")
        return settle
    except Exception as e:
        print(f"[L1] BU0结算价失败: {e}")
        return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    spot, actual_date = fetch_spot(obs_date)
    if spot is None:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            print(f"[L4] 兜底: {val}")
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                       source="db_回补", source_confidence=0.5)
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    fut = fetch_fut_settle(obs_date)
    if fut is None:
        print(f"[WARN] BU0结算价获取失败，跳过基差")
        sys.exit(0)

    basis = round(spot - fut, 2)
    if not (BOUNDS[0] <= basis <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={basis} 超出bounds{BOUNDS}，跳过")
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, basis,
               source="akshare_futures_spot+main_sina", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={basis} (现货{spot}-期货结算价{fut})")
