#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算期现基差
因子: RB_SPD_BASIS = 计算期现基差

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
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback

import akshare as ak

FACTOR_CODE = "RB_SPD_BASIS"
SYMBOL = "RB"

def fetch_futures_price():
    try:
        print("[期货] AKShare futures_main_sina RB0...")
        df = ak.futures_main_sina(symbol="RB0")
        if df is not None and len(df) > 0:
            cols = df.columns.tolist()
            price_col = None
            for c in cols:
                if 'close' in str(c).lower() or '收盘' in str(c):
                    price_col = c; break
            if price_col is None:
                price_col = cols[4] if len(cols) > 4 else cols[-1]
            return float(df.iloc[-1][price_col])
    except Exception as e:
        print(f"[期货] 失败: {e}")
    return None

def fetch_spot_price():
    # L1: 东方财富建材现货（尝试免费）
    try:
        print("[现货L1] 东方财富建材数据...")
        # TODO: 东方财富建材螺纹钢现货价
    except Exception as e:
        print(f"[现货L1] 失败: {e}")
    
    # L2: 我的钢铁网（付费）
    print("[现货L2] 我的钢铁网 - 付费订阅，跳过")
    
    # L3: 兰格钢铁网（备用付费）
    print("[现货L3] 兰格钢铁网 - 付费订阅，跳过")
    return None

def fetch_basis():
    futures = fetch_futures_price()
    if futures is None:
        print("[失败] 无法获取期货价格")
        return None, None, None
    print(f"  期货价格: {futures} 元/吨")
    
    spot = fetch_spot_price()
    if spot is not None:
        basis = spot - futures
        return basis, 'mysteel', 0.8
    
    # L4: DB回补
    print("[L4] DB历史基差回补...")
    # L4: DB回补 (moved to main)
    return None, None, None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("非交易日，跳过"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_basis()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value, source_confidence=confidence, source=source)
    else:
        print(f"[失败] {FACTOR_CODE} 现货价需付费订阅")
