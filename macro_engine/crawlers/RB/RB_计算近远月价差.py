#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算近远月价差
因子: RB_SPD_CONTRACT = 计算近远月价差

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
import requests
import datetime

FACTOR_CODE = "RB_SPD_CONTRACT"
SYMBOL = "RB"

def get_contracts():
    today = datetime.date.today()
    y, m = today.year, today.month
    months = [1, 5, 10]
    future_months = []
    for my in range(y, y+2):
        for mm in months:
            dt = datetime.date(my, mm, 1)
            if dt > today:
                future_months.append((dt, f"RB{str(my)[2:]}{mm:02d}"))
    future_months.sort(key=lambda x: x[0])
    return future_months[:2] if len(future_months) >= 2 else None

def fetch_spread():
    contracts = get_contracts()
    if not contracts:
        print("[错误] 无法确定合约代码")
        return None, None, None
    
    near_code = contracts[0][1]
    far_code = contracts[1][1]
    print(f"  近月: {near_code}, 远月: {far_code}")
    
    try:
        print("[L1] 新浪实时API...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"http://hq.sinajs.cn/list=nf_{near_code},nf_{far_code}"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        if resp.status_code == 200 and resp.text:
            lines = resp.text.strip().split('\n')
            prices = []
            for line in lines:
                if '"' in line:
                    parts = line.split('"')[1].split(',')
                    if len(parts) >= 5:
                        prices.append(float(parts[4]))
            if len(prices) >= 2:
                spread = prices[0] - prices[1]
                print(f"[L1] 成功: {spread} 元/吨")
                return spread, 'sina', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    try:
        print("[L2] AKShare futures_zh_daily_sina...")
        df1 = ak.futures_zh_daily_sina(symbol=near_code)
        df2 = ak.futures_zh_daily_sina(symbol=far_code)
        if df1 is not None and df2 is not None:
            p1 = float(df1.iloc[-1]['close'])
            p2 = float(df2.iloc[-1]['close'])
            spread = p1 - p2
            print(f"[L2] 成功: {spread} 元/吨")
            return spread, 'akshare', 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    print("[L4] DB历史回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] 兜底: {val}")
        return val, 'db_回补', 0.5
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("非交易日，跳过"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_spread()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[失败] {FACTOR_CODE} 所有数据源均失败")
