#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
焦炭期现基差
因子: J_J_SPD_BASIS = 焦炭期现基差

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

FACTOR_CODE = "J_J_SPD_BASIS"
SYMBOL = "J"

def fetch_spot_price(obs_date):
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime('%Y%m%d')
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=['J'])
            if df is None or df.empty:
                continue
            row = df.iloc[-1]
            spot = float(row.get("near_contract_price") or row.get("spot_price") or 0)
            if spot > 0:
                print(f"[L1] J spot price({date_str}): {spot}")
                return spot, check
        except Exception as e:
            print(f"[L1] J spot({date_str}): {e}")
    return None, None

def fetch_fut_close(obs_date):
    try:
        df = ak.futures_main_sina(symbol='J0')
        if df is not None and len(df) > 0:
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'oi', 'settle']
            df['date'] = pd.to_datetime(df['date'])
            mask = df['date'] <= pd.Timestamp(obs_date)
            if mask.sum() == 0:
                row = df.iloc[-1]
            else:
                row = df[mask].iloc[-1]
            close = row.get('close') or row.get('settle')
            if close is not None and not pd.isna(close):
                close = float(close)
                print(f"[L1] J0 settle: {close}")
                return close
    except Exception as e:
        print(f"[L1] J0 fut price failed: {e}")
    return None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    
    spot_price, actual_date = fetch_spot_price(obs_date)
    fut_price = fetch_fut_close(obs_date)
    
    if spot_price is not None and fut_price is not None:
        basis = spot_price - fut_price
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, basis, source_confidence=0.9, source='derived(spot-fut_settle)')
        print(f"[OK] {FACTOR_CODE}={basis:.2f} (spot{spot_price:.2f}-fut{fut_price:.2f})")
    elif spot_price is not None:
        print(f"[WARN] Fut price unavailable, writing spot only")
        save_to_db("J_SPOT_PRICE", SYMBOL, pub_date, actual_date, spot_price, source_confidence=0.9, source='akshare_futures_spot_price')
    else:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source='db_fallback')
            print(f"[OK] {FACTOR_CODE}={val} L4 fallback OK")
        else:
            print(f"[FAIL] {FACTOR_CODE} all sources failed")
