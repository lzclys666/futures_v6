#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CU_抓取_持仓排名.py
因子: CU_POS_NET = 沪铜前20净持仓

公式: 多头持仓总和 - 空头持仓总和（主力合约）

当前状态: [⚠️待修复]
- L1: AKShare get_shfe_rank_table(date=YYYYMMDD, vars_list=['CU'])
- 已知: SHFE排名API可能返回空（非交易日或接口变更）
- L4: db_utils save_l4_fallback
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak

FACTOR_CODE = "CU_POS_NET"
SYMBOL = "CU"
BOUNDS = (-200000, 200000)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1
    try:
        date_str = obs_date.strftime('%Y%m%d')
        print(f"[L1] AKShare get_shfe_rank_table(date={date_str})...")
        r = ak.get_shfe_rank_table(date=date_str, vars_list=['CU'])
        if not r:
            raise ValueError("SHFE CU持仓排名返回空")

        contracts = {k: v for k, v in r.items() if str(k).lower().startswith('cu')}
        if not contracts:
            raise ValueError(f"无CU合约数据 keys={list(r.keys())}")

        main_contract = max(contracts.keys(),
            key=lambda k: float(contracts[k]['long_open_interest'].sum()) + float(contracts[k]['short_open_interest'].sum()))
        df = contracts[main_contract]
        long_sum = float(df['long_open_interest'].sum())
        short_sum = float(df['short_open_interest'].sum())
        raw_value = long_sum - short_sum

        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return

        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="沪铜持仓排名")

if __name__ == "__main__":
    run()
