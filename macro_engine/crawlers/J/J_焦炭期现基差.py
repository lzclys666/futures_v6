#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
J_焦炭期现基差.py
因子: J_SPD_BASIS = 焦炭期现基差

公式: J_SPD_BASIS = 焦炭现货价 - 焦炭期货主力合约收盘价（元/吨）

当前状态: [✅正常]
- L1: AKShare futures_spot_price(date, vars_list=['J']) — 现货价
- L1: AKShare futures_main_sina("J0") — 期货收盘价
- L2: 无备源（焦炭现货价仅AKShare提供）
- L3: 无付费源备选
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

数据说明:
- obs_date: 使用现货价对应的交易日期（非pub_date今天）
- pub_date: 脚本运行日期（get_pit_dates自动计算）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta

SYMBOL = "J"
FACTOR_CODE = "J_SPD_BASIS"
BOUNDS = (-300, 300)


def fetch_spot_price(obs_date):
    """L1: AKShare现货价，8天回溯"""
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
                    return spot, d
        except:
            continue
    # L2: 无备源（焦炭现货价仅AKShare提供）
    raise ValueError("J现货价L1获取失败，无L2备源")


def fetch_futures_price():
    """L1: AKShare期货收盘价"""
    df = ak.futures_main_sina(symbol="J0")
    df['日期'] = pd.to_datetime(df['日期']).dt.date
    latest = df.sort_values('日期').iloc[-1]
    return float(latest['收盘价'])


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    # L1: 现货价 - 期货价
    try:
        spot_price, spot_date = fetch_spot_price(obs_date)
        fut_close = fetch_futures_price()
        raw_value = spot_price - fut_close
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, spot_date, raw_value,
                   source='AKShare', source_confidence=0.9)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={spot_date}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")

    # L2: 无备源
    # L3: 无付费源备选

    # L4: DB历史最新值回补
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
