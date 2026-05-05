#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_CCI焦炭价格指数.py
因子: J_SPT_CCI = CCI焦炭价格指数

公式: J_SPT_CCI = CCI指数（元/吨）

当前状态: [⚠️待修复]
- L1: CCI指数需汾渭付费账号（无免费源）
- L2: AKShare futures_spot_price(date, vars_list=['JM']) — JM现货替代
- L3: 无付费源备选
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
from datetime import timedelta

SYMBOL = "J"
FACTOR_CODE = "J_SPT_CCI"
BOUNDS = (500, 5000)

def fetch():
    pub_date, obs_date = get_pit_dates()
    for delta in range(8):
        d = obs_date - timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        try:
            df = ak.futures_spot_price(date=d.strftime('%Y%m%d'), vars_list=['JM'])
            if df is not None and not df.empty:
                row = df.iloc[-1]
                spot = float(row.get("near_contract_price") or row.get("spot_price") or 0)
                if spot > 0:
                    return spot, d
        except:
            continue
    raise ValueError("CCI指数JM现货替代获取失败")

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        raw_value, obs_date = fetch()
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source='AKShare_JM替代', source_confidence=0.8)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L2 FAIL] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
