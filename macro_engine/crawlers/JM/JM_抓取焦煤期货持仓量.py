#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取焦煤期货持仓量
因子: JM_POS_OI = 抓取焦煤期货持仓量

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
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value, DB_PATH

import akshare as ak

FACTOR_CODE = "JM_POS_OI"
SYMBOL = "JM"

def fetch_oi():
    """四层漏斗获取持仓量"""
    # L1: AKShare futures_main_sina
    try:
        print("[L1] AKShare futures_main_sina...")
        df = ak.futures_main_sina(symbol="JM0")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            hold_col = None
            for c in cols:
                if 'hold' in str(c).lower() or '持仓' in str(c):
                    hold_col = c; break
            if hold_col is None:
                hold_col = cols[6] if len(cols) > 6 else cols[-1]
            val = df.iloc[-1][hold_col]
            if isinstance(val, str):
                val = val.replace(',', '').strip()
            val = float(val)
            if 0 <= val <= 1000000:
                print(f"[L1] 成功: {val} 手")
                return val, 'akshare', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: AKShare futures_zh_daily_sina
    try:
        print("[L2] AKShare futures_zh_daily_sina...")
        df = ak.futures_zh_daily_sina(symbol="JM0")
        if df is not None and len(df) > 0 and 'hold' in df.columns:
            val = float(df.iloc[-1]['hold'])
            if 0 <= val <= 1000000:
                print(f"[L2] 成功: {val} 手")
                return val, 'akshare', 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    # L3: 新浪实时API
    try:
        print("[L3] 新浪实时API...")
        import requests
        url = "http://hq.sinajs.cn/list=nf_JM0"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        if resp.status_code == 200 and resp.text:
            data = resp.text.split('"')[1].split(',') if '"' in resp.text else []
            if len(data) >= 13:
                val = float(data[11])
                if 0 <= val <= 1000000:
                    print(f"[L3] 成功: {val} 手")
                    return val, 'sina', 0.8
    except Exception as e:
        print(f"[L3] 失败: {e}")
    
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
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    
    value, source, confidence = fetch_oi()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[失败] {FACTOR_CODE} 所有数据源均失败")
