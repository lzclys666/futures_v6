#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
焦炭与焦煤价差
因子: J_J_SPD_J_JM = 焦炭与焦煤价差

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

FACTOR_CODE = "J_J_SPD_J_JM"
SYMBOL = "J"

def fetch_spot_prices(obs_date):
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime('%Y%m%d')
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=['J', 'JM'])
            if df is None or df.empty:
                continue
            j_row = df[df['symbol'] == 'J']
            jm_row = df[df['symbol'] == 'JM']
            if len(j_row) == 0 or len(jm_row) == 0:
                continue
            j_spot = float(j_row.iloc[-1].get("near_contract_price") or j_row.iloc[-1].get("spot_price") or 0)
            jm_spot = float(jm_row.iloc[-1].get("near_contract_price") or jm_row.iloc[-1].get("spot_price") or 0)
            if j_spot > 0 and jm_spot > 0:
                print(f"[L1] J/JM spot({date_str}): J={j_spot}, JM={jm_spot}")
                return j_spot, jm_spot, check
        except Exception as e:
            print(f"[L1] J/JM spot({date_str}): {e}")
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    
    j_spot, jm_spot, actual_date = fetch_spot_prices(obs_date)
    
    if j_spot is not None and jm_spot is not None:
        ratio = j_spot / jm_spot
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, ratio, source_confidence=0.9, source='derived(J_spot/JM_spot)')
        print(f"[OK] {FACTOR_CODE}={ratio:.4f} (J={j_spot:.2f}/JM={jm_spot:.2f})")
    else:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source='db_fallback')
            print(f"[OK] {FACTOR_CODE}={val} L4 fallback OK")
        else:
            print(f"[FAIL] {FACTOR_CODE} all sources failed")
