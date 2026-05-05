#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JM_计算焦煤期现基差.py
因子: JM_SPD_BASIS = 焦煤期现基差

公式: JM_SPD_BASIS = 焦煤现货价 - 焦煤期货主力合约收盘价（元/吨）

当前状态: [⚠️待修复]
- L1: AKShare futures_main_sina("JM0") — 期货收盘价 ✅
- L1: 焦煤现货价（蒙5#折盘面）— 需汾渭/Mysteel付费订阅
- L2: 无备源（焦煤现货价仅付费渠道提供）
- L3: 付费订阅: 汾渭能源（年费）/ Mysteel（年费）
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

数据说明:
- 现货价需汾渭/Mysteel付费订阅，接入后自动生效
- 无现货价时走L4回补
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak

SYMBOL = "JM"
FACTOR_CODE = "JM_SPD_BASIS"
BOUNDS = (-500, 500)
# 付费来源: 汾渭能源(年费) / Mysteel(年费) 提供蒙5#折盘面价


def fetch_futures_price():
    """L1: 获取焦煤期货主力价格"""
    df = ak.futures_main_sina(symbol="JM0")
    if df is not None and len(df) > 0:
        cols = df.columns.tolist()
        price_col = None
        for c in cols:
            if 'close' in str(c).lower() or '收盘' in str(c):
                price_col = c
                break
        if price_col is None:
            price_col = cols[4] if len(cols) > 4 else cols[-1]
        return float(df.iloc[-1][price_col])
    return None


def fetch_spot_price():
    """L1: 获取焦煤现货价(蒙5#折盘面)"""
    # L1: 汾渭能源 - 付费
    print("[现货L1] 汾渭能源蒙5#折盘面价 - 付费订阅，跳过")
    # L2: Mysteel - 付费
    print("[现货L2] Mysteel蒙煤报价 - 付费订阅，跳过")
    # L3: 无备源（焦煤现货价仅付费渠道提供）
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()

    # L1: 期货价
    try:
        futures_price = fetch_futures_price()
        if futures_price is None:
            raise ValueError("期货价格获取失败")
        print(f"  期货价格: {futures_price} 元/吨")

        # L1: 现货价
        spot_price = fetch_spot_price()
        if spot_price is not None:
            raw_value = spot_price - futures_price
            if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
                print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
                return
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                       source_confidence=0.8, source='汾渭/Mysteel')
            print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
            return
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")

    # L2: 无备源
    # L3: 付费订阅（需人工接入）

    # L4: DB历史最新值回补
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)

    # L5: 不写NULL占位符（SOP§7）


if __name__ == "__main__":
    main()
