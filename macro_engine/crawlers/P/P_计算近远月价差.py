#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P_棕榈油近远月价差.py
因子: P_SPD_CONTRACT = 棕榈油近远月价差（元/吨）

公式: P_SPD_CONTRACT = P主力合约收盘价 - P次主力合约收盘价

当前状态: ✅正常
- L1: AKShare futures_zh_daily_sina(symbol) — 遍历当年及次年合约，取持仓量前二计算价差
- L4: save_l4_fallback() DB历史最新值回补

已验证: 2026-05-06 P2609=9864 P2701=9911 价差=-47
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import datetime

FCODE = "P_SPD_CONTRACT"
SYM = "P"
BOUNDS = (-1000, 1000)


def get_active_contracts():
    """获取P当前活跃合约（持仓量>0），按持仓量排序取前二"""
    today = datetime.date.today()
    y = today.year
    candidates = []
    for dy in range(2):
        for m in [1, 5, 9, 10, 12]:
            yy = y + dy
            code = f"P{str(yy)[2:]}{m:02d}"
            try:
                df = ak.futures_zh_daily_sina(symbol=code)
                if df is not None and len(df) > 0:
                    last = df.iloc[-1]
                    close = float(last['close'])
                    hold = float(last.get('hold', 0))
                    if hold > 0:
                        candidates.append((code, close, hold))
                        print(f"  {code}: close={close:.0f} hold={hold:.0f}")
            except Exception as e:
                print(f"  {code}: {type(e).__name__}: {str(e)[:60]}")
    # Sort by open interest descending, take top 2
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates[:2]


def fetch():
    """L1: 计算主力-次主力价差"""
    contracts = get_active_contracts()
    if len(contracts) < 2:
        print(f"  不足2个活跃合约")
        return None

    main_code, main_price, main_hold = contracts[0]
    sub_code, sub_price, sub_hold = contracts[1]
    spread = main_price - sub_price
    print(f"  主力: {main_code}={main_price:.0f}(OI={main_hold:.0f}), "
          f"次主力: {sub_code}={sub_price:.0f}(OI={sub_hold:.0f}), 价差={spread:.0f}")
    return spread


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value = fetch()
        if raw_value is None:
            print(f"[L1] {FCODE}: 数据不足")
            save_l4_fallback(FCODE, SYM, pub_date, obs_date)
            return
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FCODE}={raw_value} out of {BOUNDS}")
            return
        save_to_db(FCODE, SYM, pub_date, obs_date, raw_value,
                   source_confidence=1.0, source='akshare_sina_P_contracts')
        print(f"[OK] {FCODE}={raw_value:.0f} obs={obs_date}")
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {type(e).__name__}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)


if __name__ == "__main__":
    main()
