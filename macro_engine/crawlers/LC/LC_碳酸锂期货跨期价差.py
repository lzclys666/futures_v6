#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LC_碳酸锂期货跨期价差.py
因子: LC_SPD_01 = 碳酸锂主力-次主力价差（1个合约月后）
因子: LC_SPD_03 = 碳酸锂主力-远月价差（3个合约月后）
因子: LC_SPD_05 = 碳酸锂主力-超远月价差（5个合约月后）

公式: SPD = 主力合约收盘价 - 目标合约收盘价

当前状态: [✅正常]
- L1: AKShare futures_zh_daily_sina 获取各合约收盘价，source_confidence=1.0
- L4: db_utils save_l4_fallback
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak
import pandas as pd
import datetime

SYMBOL = "LC"
# LC 交易月份: 01-12（全年所有月份）
LC_MONTHS = list(range(1, 13))
BOUNDS = (-50000, 50000)

FACTOR_DEFS = [
    ("LC_SPD_01", 1),  # 1个合约月后
    ("LC_SPD_03", 3),  # 3个合约月后
    ("LC_SPD_05", 5),  # 5个合约月后
]


def get_active_contracts():
    """获取所有活跃的LC合约及其最新价格"""
    today = datetime.date.today()
    contracts = []
    
    for y in range(today.year, today.year + 2):
        for m in LC_MONTHS:
            code = f"LC{str(y)[2:]}{m:02d}"
            try:
                df = ak.futures_zh_daily_sina(symbol=code)
                if df is not None and len(df) > 0:
                    latest = df.iloc[-1]
                    close = float(latest['close'])
                    hold = float(latest['hold'])
                    obs_date = pd.to_datetime(latest['date']).date()
                    if hold > 0:  # 只要持仓量>0的活跃合约
                        contracts.append({
                            'code': code,
                            'year': y,
                            'month': m,
                            'close': close,
                            'hold': hold,
                            'obs_date': obs_date,
                        })
            except Exception:
                pass
    
    contracts.sort(key=lambda x: (x['year'], x['month']))
    return contracts


def find_main_contract(contracts):
    """找主力合约（持仓量最大）"""
    if not contracts:
        return None
    return max(contracts, key=lambda x: x['hold'])


def find_nth_after_main(contracts, main, n):
    """找主力合约之后的第n个合约"""
    main_idx = None
    for i, c in enumerate(contracts):
        if c['code'] == main['code']:
            main_idx = i
            break
    if main_idx is None:
        return None
    target_idx = main_idx + n
    if target_idx < len(contracts):
        return contracts[target_idx]
    return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== LC跨期价差 === pub={pub_date} obs={obs_date}")

    contracts = get_active_contracts()
    if len(contracts) < 2:
        print(f"[ERR] 活跃合约不足: {len(contracts)}")
        for fcode, _ in FACTOR_DEFS:
            save_l4_fallback(fcode, SYMBOL, pub_date, obs_date, extra_msg="碳酸锂跨期价差")
        return

    main = find_main_contract(contracts)
    print(f"主力合约: {main['code']} close={main['close']} hold={main['hold']}")
    print(f"活跃合约: {[c['code'] for c in contracts]}")

    for fcode, offset in FACTOR_DEFS:
        target = find_nth_after_main(contracts, main, offset)
        if target is None:
            print(f"[SKIP] {fcode} 无法找到主力后第{offset}个合约")
            save_l4_fallback(fcode, SYMBOL, pub_date, obs_date, extra_msg="碳酸锂跨期价差")
            continue

        spread = round(main['close'] - target['close'], 2)

        if not (BOUNDS[0] <= spread <= BOUNDS[1]):
            print(f"[WARN] {fcode}={spread} (main={main['code']} - target={target['code']}) out of {BOUNDS}")
            save_l4_fallback(fcode, SYMBOL, pub_date, obs_date, extra_msg="碳酸锂跨期价差")
            continue

        save_to_db(fcode, SYMBOL, pub_date, obs_date, spread, source_confidence=1.0)
        print(f"[OK] {fcode}={spread} ({main['code']}-{target['code']}) obs={obs_date}")


if __name__ == "__main__":
    main()
