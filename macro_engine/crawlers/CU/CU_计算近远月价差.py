#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CU_计算_近远月价差.py
因子: CU_SPD_CONTRACT = 沪铜近远月价差

公式: 近月合约价 - 主力合约价

当前状态: [✅正常]
- L1: AKShare futures_spot_price(vars_list=['CU']) 获取 near_contract_price - dominant_contract_price
- L4: db_utils save_l4_fallback
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak

FACTOR_CODE = "CU_SPD_CONTRACT"
SYMBOL = "CU"
BOUNDS = (-300, 300)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1
    try:
        date_str = obs_date.strftime('%Y%m%d')
        print(f"[L1] AKShare futures_spot_price(date={date_str}, vars_list=['CU'])...")
        df = ak.futures_spot_price(date=date_str, vars_list=['CU'])
        if df.empty:
            raise ValueError("返回空")
        row = df.iloc[0]
        near_price = float(row['near_contract_price'])
        dom_price = float(row['dominant_contract_price'])
        raw_value = near_price - dom_price

        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return

        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="沪铜近远月价差")

if __name__ == "__main__":
    run()
