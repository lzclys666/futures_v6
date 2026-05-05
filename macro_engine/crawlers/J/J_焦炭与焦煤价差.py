#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭与焦煤价差.py
因子: J_SPD_J_JM = 焦炭/焦煤比价

公式: J_SPD_J_JM = 焦炭现货价 / 焦煤现货价

当前状态: [✅正常]
- L1: AKShare futures_spot_price(date, vars_list=['J','JM']) — J和JM现货价
- L2: 无备源（焦炭/焦煤现货价仅AKShare提供）
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
FACTOR_CODE = "J_SPD_J_JM"
BOUNDS = (0.5, 3.0)

def fetch():
    pub_date, obs_date = get_pit_dates()
    for delta in range(8):
        d = obs_date - timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        try:
            df = ak.futures_spot_price(date=d.strftime('%Y%m%d'), vars_list=['J', 'JM'])
            if df is None or df.empty:
                continue
            j_row = df[df['symbol'] == 'J']
            jm_row = df[df['symbol'] == 'JM']
            if len(j_row) == 0 or len(jm_row) == 0:
                continue
            j_spot = float(j_row.iloc[-1].get("near_contract_price") or j_row.iloc[-1].get("spot_price") or 0)
            jm_spot = float(jm_row.iloc[-1].get("near_contract_price") or jm_row.iloc[-1].get("spot_price") or 0)
            if j_spot > 0 and jm_spot > 0:
                return j_spot / jm_spot, d
        except:
            continue
    raise ValueError("J/JM现货价获取失败")

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        raw_value, obs_date = fetch()
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source='AKShare', source_confidence=0.9)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
