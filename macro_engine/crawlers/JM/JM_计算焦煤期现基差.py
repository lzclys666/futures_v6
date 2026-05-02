#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算焦煤期现基差
因子: JM_SPD_BASIS = 计算焦煤期现基差

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

FACTOR_CODE = "JM_SPD_BASIS"
SYMBOL = "JM"
# 付费来源: 汾渭能源(年费) / Mysteel(年费) 提供蒙5#折盘面价

def fetch_futures_price():
    """获取焦煤期货主力价格"""
    try:
        df = ak.futures_main_sina(symbol="JM0")
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
        print(f"[期货价] 获取失败: {e}")
    return None

def fetch_spot_price():
    """获取焦煤现货价(蒙5#折盘面)"""
    # L1: 汾渭能源 - 付费
    print("[现货L1] 汾渭能源蒙5#折盘面价 - 付费订阅，跳过")
    # L2: Mysteel - 付费
    print("[现货L2] Mysteel蒙煤报价 - 付费订阅，跳过")
    # L3: 隆众资讯/生意社 - 尝试免费
    try:
        print("[现货L3] 尝试隆众资讯...")
        # TODO: 隆众 oilchem.net 焦煤现货价格页面爬取
        # 需要解析网页，暂时不可用
    except:
        pass
    return None

def fetch_basis():
    """四层漏斗"""
    futures_price = fetch_futures_price()
    if futures_price is None:
        print("[失败] 无法获取期货价格")
        return None, None, None
    
    print(f"  期货价格: {futures_price} 元/吨")
    
    spot_price = fetch_spot_price()
    if spot_price is not None:
        basis = spot_price - futures_price
        return basis, '汾渭/Mysteel', 0.8
    
    # 无现货价，L4兜底: 用历史最新基差
    print("[L4] 无现货价，DB历史基差回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] 兜底基差: {val}")
        return val, 'db_回补(无现货价)', 0.5
    
    print("[失败] 现货价不可用且无历史数据")
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
        print(f"[失败] {FACTOR_CODE} 现货价需付费订阅，接入后自动生效")
