#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
我的钢铁网焦炭现货价格
因子: J_J_SPT_MYSTEEEL = 我的钢铁网焦炭现货价格

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

from common.web_utils import fetch_url, fetch_json
import akshare as ak
import pandas as pd
from datetime import timedelta

FACTOR_CODE = "J_J_SPT_MYSTEEEL"
SYMBOL = "J"

def fetch_mysteel_price():
    url = "https://index.mysteel.com/api/market/price/getMarketPrice.html?itemCode=13570276448&date="
    headers = {
        'Referer': 'https://index.mysteel.com/',
        'Accept': 'application/json, text/plain, */*'
    }
    try:
        data, err = fetch_json(url, headers=headers, timeout=10)
        if not err:
            if isinstance(data, dict) and 'data' in data:
                price = float(data['data'].get('price', 0))
                if price > 0:
                    print(f"[L1] Mysteel coke price: {price}")
                    return price, 'mysteel_public', 1.0
    except Exception as e:
        print(f"[L1] Mysteel failed: {e}")
    return None, None, None

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
                print(f"[L2] AKShare J spot({date_str}): {spot}")
                return spot, check
        except Exception as e:
            print(f"[L2] AKShare J spot({date_str}): {e}")
    return None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    
    price, source, conf = fetch_mysteel_price()
    actual_date = obs_date
    
    if price is None:
        price, actual_date = fetch_spot_price(obs_date)
        if price is not None:
            source = 'akshare_futures_spot_price(alternative)'
            conf = 0.8
    
    if price is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, price, source_confidence=conf, source=source)
        print(f"[OK] {FACTOR_CODE}={price:.2f} written")
    else:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source='db_fallback')
            print(f"[OK] {FACTOR_CODE}={val} L4 fallback OK")
        else:
            print(f"[FAIL] {FACTOR_CODE} all sources failed")
