#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沥青与布伦特原油价差
因子: BU_BU_SPD_BU_BRENT = 沥青与布伦特原油价差

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
import pandas as pd

FACTOR_CODE = "BU_BU_SPD_BU_BRENT"
SYMBOL = "BU"

def fetch_bu_price(obs_date):
    try:
        df = ak.futures_main_sina(symbol='BU0')
        if df is not None and len(df) > 0:
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'oi', 'settle']
            df['date'] = pd.to_datetime(df['date'])
            mask = df['date'] <= pd.Timestamp(obs_date)
            row = df[mask].iloc[-1] if mask.sum() > 0 else df.iloc[-1]
            return float(row.get('close') or row.get('settle') or 0)
    except Exception as e:
        print(f"[WARN] BU price: {e}")
    return None

def fetch_sc_price(obs_date):
    try:
        df = ak.futures_main_sina(symbol='SC0')
        if df is not None and len(df) > 0:
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'oi', 'settle']
            df['date'] = pd.to_datetime(df['date'])
            mask = df['date'] <= pd.Timestamp(obs_date)
            row = df[mask].iloc[-1] if mask.sum() > 0 else df.iloc[-1]
            price = float(row.get('close') or row.get('settle') or 0)
            if price > 0:
                print(f"[L2] SC crude({row['date'].date()}): {price} (as Brent alternative)")
                return price
    except Exception as e:
        print(f"[L2] SC crude: {e}")
    return None

if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    print("[NOTE] Brent crude has no free AKShare source, using SC crude futures as alternative")
    
    bu_price = fetch_bu_price(obs_date)
    brent_price = fetch_sc_price(obs_date)
    
    if bu_price is not None and brent_price is not None and brent_price > 0:
        ratio = bu_price / brent_price
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, ratio, source_confidence=0.8, source='derived(BU/SC替代Brent)')
        print(f"[OK] {FACTOR_CODE}={ratio:.4f} (BU={bu_price:.1f}/SC={brent_price:.1f})")
    elif bu_price is not None:
        print(f"[WARN] Only BU price available ({bu_price}), Brent unavailable")
    else:
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=0.5, source='db_fallback')
            print(f"[OK] {FACTOR_CODE}={val} L4 fallback OK")
        else:
            print(f"[SKIP] {FACTOR_CODE} no data")
