#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_计算焦煤动力煤比价.py
因子: JM_SPD_ZC = 焦煤/动力煤比价

公式: JM_SPD_ZC = 焦煤期货主力收盘价 / 动力煤期货主力收盘价

当前状态: [✅正常]
- L1: AKShare futures_main_sina("JM0") / futures_main_sina("ZC0") — 期货比价
- L2: 无备源（期货价格仅新浪提供）
- L3: 无付费源备选
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak

SYMBOL = "JM"
FACTOR_CODE = "JM_SPD_ZC"
BOUNDS = (0.5, 3.0)


def fetch_jm_price():
    """L1: 获取焦煤期货主力价格"""
    df = ak.futures_main_sina(symbol="JM0")
    if df is not None and len(df) > 0:
        latest = df.iloc[-1]
        if 'settle' in df.columns:
            return float(latest['settle'])
        elif 'close' in df.columns:
            return float(latest['close'])
        else:
            return float(latest.iloc[4])
    return None


def fetch_zc_price():
    """L1: 获取动力煤期货主力价格"""
    df = ak.futures_main_sina(symbol="ZC0")
    if df is not None and len(df) > 0:
        latest = df.iloc[-1]
        if 'settle' in df.columns:
            return float(latest['settle'])
        elif 'close' in df.columns:
            return float(latest['close'])
        else:
            return float(latest.iloc[4])
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    # L1: 焦煤/动力煤比价
    try:
        jm_price = fetch_jm_price()
        if jm_price is None:
            raise ValueError("焦煤价格获取失败")
        zc_price = fetch_zc_price()
        if zc_price is None:
            raise ValueError("动力煤价格获取失败")

        ratio = jm_price / zc_price
        print(f"[L1] 焦煤/动力煤 = {jm_price}/{zc_price} = {ratio:.4f}")

        if not (BOUNDS[0] <= ratio <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={ratio:.4f} out of {BOUNDS}")
            return
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, ratio,
                   source_confidence=0.9, source='akshare')
        print(f"[OK] {FACTOR_CODE}={ratio:.4f} obs={obs_date}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")

    # L2: 无备源（期货价格仅新浪提供）
    # L3: 无付费源备选

    # L4: DB历史最新值回补
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
