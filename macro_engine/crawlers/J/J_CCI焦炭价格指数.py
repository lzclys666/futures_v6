#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCI焦炭价格指数
因子: J_J_SPT_CCI = CCI焦炭价格指数

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd
from datetime import timedelta

FACTOR_CODE = "J_J_SPT_CCI"
SYMBOL = "J"

def fetch_jm_spot(obs_date):
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime('%Y%m%d')
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=['JM'])
            if df is None or df.empty:
                continue
            row = df.iloc[-1]
            spot = float(row.get("near_contract_price") or row.get("spot_price") or 0)
            if spot > 0:
                print(f"[L2] JM spot({date_str}): {spot} (as CCI alternative)")
                return spot, check
        except Exception as e:
            print(f"[L2] JM spot({date_str}): {e}")
    return None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print("[NOTE] CCI coking coal price needs Fenwei paid account, using JM spot as alternative")
    
    value, actual_date = fetch_jm_spot(obs_date)
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, value, source_confidence=0.8, source='akshare_futures_spot_price_JM(alternative_CCI)')
        print(f"[OK] {FACTOR_CODE}={value:.2f} written")
    else:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source='db_fallback')
            print(f"[OK] {FACTOR_CODE}={val} L4 fallback OK")
        else:
            print(f"[SKIP] {FACTOR_CODE} no data")
