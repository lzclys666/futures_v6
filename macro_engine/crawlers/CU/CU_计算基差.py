#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CU_计算_基差.py
因子: CU_SPD_BASIS = 沪铜期现基差

公式: 现货价 - 期货结算价

当前状态: [✅正常]
- L1: AKShare futures_spot_price(vars_list=['CU']) 获取现货价 + futures_main_sina('cu0') 获取期货价
- L4: db_utils save_l4_fallback
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import date, timedelta

FACTOR_CODE = "CU_SPD_BASIS"
SYMBOL = "CU"
BOUNDS = (-500, 500)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1: 现货 + 期货 → 基差
    try:
        date_str = obs_date.strftime('%Y%m%d')
        print(f"[L1] AKShare futures_spot_price(date={date_str}, vars_list=['CU'])...")
        df_spot = ak.futures_spot_price(date=date_str, vars_list=['CU'])
        if df_spot.empty:
            raise ValueError("现货价返回空")
        spot_price = float(df_spot.iloc[0]['near_basis'])
        print(f"[L1] 现货基差字段={spot_price}")

        # 也需要现货价和期货价来计算
        print("[L1] AKShare futures_main_sina(symbol='cu0')...")
        df_fut = ak.futures_main_sina(symbol="cu0")
        if df_fut.empty:
            raise ValueError("期货价返回空")
        df_fut['日期'] = pd.to_datetime(df_fut['日期']).dt.date
        latest_fut = df_fut.sort_values('日期').iloc[-1]
        fut_price = float(latest_fut['收盘价'])
        raw_value = spot_price  # near_basis 已经是基差
        obs = latest_fut['日期']

        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            return

        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs, raw_value, source_confidence=1.0)
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="沪铜基差")

if __name__ == "__main__":
    run()
