#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算螺纹钢热卷比价
因子: RB_SPD_RB_HC = 计算螺纹钢热卷比价

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
from common.web_utils import fetch_url

import akshare as ak

FACTOR_CODE = "RB_SPD_RB_HC"
SYMBOL = "RB"

def fetch_ratio():
    # L1: 新浪实时API - RB0 和 HC0
    try:
        print("[L1] 新浪实时API RB0 & HC0...")
        url = "http://hq.sinajs.cn/list=nf_RB0,nf_HC0"
        html, err = fetch_url(url, timeout=10)
        if not err and html:
            lines = html.strip().split('\n')
            prices = []
            for line in lines:
                if '"' in line:
                    parts = line.split('"')[1].split(',')
                    if len(parts) >= 5:
                        prices.append(float(parts[4]))
            if len(prices) >= 2 and prices[1] > 0:
                ratio = prices[0] / prices[1]
                print(f"[L1] 成功: RB/HC={ratio:.4f} (RB={prices[0]:.0f}, HC={prices[1]:.0f})")
                return ratio, 'sina', 1.0
    except Exception as e:
        print(f"[L1] 失败: {e}")
    
    # L2: AKShare 日线数据
    try:
        print("[L2] AKShare futures_zh_daily_sina...")
        df_rb = ak.futures_zh_daily_sina(symbol="RB0")
        df_hc = ak.futures_zh_daily_sina(symbol="HC0")
        if df_rb is not None and df_hc is not None:
            p_rb = float(df_rb.iloc[-1]['close'])
            p_hc = float(df_hc.iloc[-1]['close'])
            if p_hc > 0:
                ratio = p_rb / p_hc
                print(f"[L2] 成功: RB/HC={ratio:.4f}")
                return ratio, 'akshare', 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")
    
    # L4: DB回补
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
    value, source, confidence = fetch_ratio()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[失败] {FACTOR_CODE} 所有数据源均失败")
