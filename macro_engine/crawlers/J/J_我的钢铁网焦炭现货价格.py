#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_我的钢铁网焦炭现货价格.py
因子: J_SPT_MYSTEL = 我的钢铁网焦炭现货价格

公式: J_SPT_MYSTEL = 焦炭现货价（元/吨）

当前状态: [✅正常]
- L1: Mysteel公共API — index.mysteel.com
- L2: AKShare futures_spot_price(date, vars_list=['J']) — AKShare现货价
- L3: 无付费源备选
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
from web_utils import fetch_json
import akshare as ak
from datetime import timedelta

SYMBOL = "J"
FACTOR_CODE = "J_SPT_MYSTEL"
BOUNDS = (500, 5000)

def fetch():
    pub_date, obs_date = get_pit_dates()

    # L1: Mysteel
    try:
        url = "https://index.mysteel.com/api/market/price/getMarketPrice.html?itemCode=13570276448&date="
        headers = {'Referer': 'https://index.mysteel.com/', 'Accept': 'application/json'}
        data, err = fetch_json(url, headers=headers, timeout=10)
        if not err and isinstance(data, dict) and 'data' in data:
            price = float(data['data'].get('price', 0))
            if price > 0:
                return price, obs_date, 'mysteel_public', 1.0
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L2: AKShare
    for delta in range(8):
        d = obs_date - timedelta(days=delta)
        if d.weekday() >= 5:
            continue
        try:
            df = ak.futures_spot_price(date=d.strftime('%Y%m%d'), vars_list=['J'])
            if df is not None and not df.empty:
                row = df.iloc[-1]
                spot = float(row.get("near_contract_price") or row.get("spot_price") or 0)
                if spot > 0:
                    return spot, d, 'AKShare', 0.9
        except:
            continue

    raise ValueError("J现货价L1+L2全部失败")

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    try:
        raw_value, obs_date, source, conf = fetch()
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source=source, source_confidence=conf)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
    except Exception as e:
        print(f"[L1+L2 FAIL] {FACTOR_CODE}: {e}")
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
