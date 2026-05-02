#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算焦煤月差
因子: JM_SPD_CONTRACT = 计算焦煤月差

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""

import sys
import os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import requests
import datetime

FACTOR_CODE = "JM_SPD_CONTRACT"
SYMBOL = "JM"

def get_active_contracts():
    """获取大商所焦煤活跃合约列表(1,5,9月)"""
    today = datetime.date.today()
    y, m = today.year, today.month
    months = [1, 5, 9]
    contracts = []
    for my in range(y, y+2):
        for mm in months:
            dt = datetime.date(my, mm, 1)
            if dt > today - datetime.timedelta(days=30):
                contracts.append(f"JM{str(my)[2:]}{mm:02d}")
    return sorted(contracts)

def fetch_contract_settle(contract):
    """获取单个合约最新结算价"""
    try:
        df = ak.futures_zh_daily_sina(symbol=contract)
        if df is not None and len(df) > 0 and 'settle' in df.columns:
            settle = float(df.iloc[-1]['settle'])
            hold = float(df.iloc[-1]['hold'])
            return settle, hold
    except:
        pass
    return None, None

def fetch_spread():
    """四层漏斗获取月差"""
    contracts = get_active_contracts()
    print(f"  候选合约: {contracts}")
    
    # L1: AKShare 多合约结算价
    try:
        print("[L1] AKShare futures_zh_daily_sina 多合约...")
        results = []
        for c in contracts:
            settle, hold = fetch_contract_settle(c)
            if settle and hold and hold > 0:
                results.append((c, settle, hold))
                print(f"    {c}: settle={settle}, hold={hold}")
        
        if len(results) >= 2:
            # 按持仓量排序取前两个
            results.sort(key=lambda x: x[2], reverse=True)
            near = results[0]
            far = results[1] if results[1][2] > 10000 else (results[-1] if len(results) > 2 else None)
            if far:
                spread = near[1] - far[1]
                print(f"[L1] 成功: {near[0]}({near[1]}) - {far[0]}({far[1]}) = {spread}")
                return spread, 'akshare', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: 新浪实时API
    try:
        print("[L2] 新浪实时API...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        if len(contracts) >= 2:
            url = f"http://hq.sinajs.cn/list=nf_{contracts[0]},nf_{contracts[1]}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'gbk'
            if resp.status_code == 200 and resp.text:
                lines = resp.text.strip().split('\n')
                prices = []
                for line in lines:
                    if '"' in line:
                        parts = line.split('"')[1].split(',')
                        if len(parts) >= 5 and parts[4]:
                            prices.append(float(parts[4]))
                if len(prices) >= 2:
                    spread = prices[0] - prices[1]
                    print(f"[L2] 成功: {spread}")
                    return spread, 'sina', 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    # L4: DB兜底
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
    print(f"=== {FACTOR_CODE} ===")
    print(f"pub_date: {pub_date}")
    print(f"obs_date: {obs_date}")
    
    value, source, confidence = fetch_spread()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, 
                  source_confidence=confidence, source=source)
        print(f"✅ 写入数据: {value}")
    else:
        print(f"[失败] {FACTOR_CODE} 所有数据源均失败")
