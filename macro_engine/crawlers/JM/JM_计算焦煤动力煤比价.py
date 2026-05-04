#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算焦煤动力煤比价
因子: JM_SPD_ZC = 焦煤/动力煤比价

公式: JM期货价 / ZC期货价

当前状态: [WARN] 待修复
- 添加 bounds 检查 (0.5, 3.0)
- Header 待完善

订阅优先级: [免费-AKShare]
替代付费源: 汾渭能源(动力煤现货)
"""
import sys
import os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates
import akshare as ak
import datetime

FACTOR_CODE = "JM_SPD_ZC"
SYMBOL = "JM"

def fetch_jm_price():
    """获取焦煤期货主力价格"""
    try:
        print("[焦煤] 获取期货价格...")
        df = ak.futures_main_sina(symbol="JM0")
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            # 获取结算价或收盘价
            price = None
            if 'settle' in df.columns:
                price = float(latest['settle'])
            elif 'close' in df.columns:
                price = float(latest['close'])
            else:
                price = float(latest.iloc[4])  # 第5列通常是收盘价
            
            print(f"[焦煤] 主力合约价格: {price} 元/吨")
            return price
    except Exception as e:
        print(f"[焦煤] 获取失败: {e}")
    return None

def fetch_zc_price():
    """获取动力煤价格"""
    # L1: AKShare 动力煤期货
    try:
        print("[动力煤] 尝试期货价格...")
        df = ak.futures_main_sina(symbol="ZC0")
        if df is not None and len(df) > 0:
            latest = df.iloc[-1]
            price = None
            if 'settle' in df.columns:
                price = float(latest['settle'])
            elif 'close' in df.columns:
                price = float(latest['close'])
            else:
                price = float(latest.iloc[4])
            
            print(f"[动力煤] 期货价格: {price} 元/吨")
            return price
    except Exception as e:
        print(f"[动力煤] 期货获取失败: {e}")
    
    # L2: 秦皇岛煤炭网现货价（需爬虫，暂用参考值）
    try:
        print("[动力煤] 尝试现货价格...")
        # TODO: 接入秦皇岛煤炭网或汾渭动力煤现货价
        print("[动力煤] 现货数据需付费订阅，暂用期货价格替代")
        return None
    except Exception as e:
        print(f"[动力煤] 现货获取失败: {e}")
        return None

def main():
    print("=" * 60)
    print(f"焦煤（JM）因子采集: {FACTOR_CODE}")
    print("=" * 60)
    
    ensure_table()
    
    # PIT日期处理
    pub_date, obs_date = get_pit_dates(freq="日频")
    if pub_date is None:
        print("周日非交易日，跳过")
        return
    
    print(f"pub_date: {pub_date}")
    print(f"obs_date: {obs_date}")
    
    # 获取焦煤价格
    jm_price = fetch_jm_price()
    if jm_price is None:
        print("[失败] 无法获取焦煤价格")
        return
    
    # 获取动力煤价格
    zc_price = fetch_zc_price()
    if zc_price is None:
        print("[失败] 无法获取动力煤价格")
        return
    
    # 计算比价
    ratio = jm_price / zc_price
    print(f"[计算] 焦煤/动力煤比价 = {jm_price} / {zc_price} = {ratio:.4f}")
    
    # Bounds 检查: (0.5, 3.0)
    expected_lo, expected_hi = 0.5, 3.0
    if not (expected_lo <= ratio <= expected_hi):
        print(f"[WARN] {FACTOR_CODE}={ratio:.4f} 超出bounds[{expected_lo}, {expected_hi}]，跳过")
        return
    
    # 写入数据库
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, ratio,
               source_confidence=0.9, source='akshare')
    print(f"[成功] {FACTOR_CODE} = {ratio:.4f}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
