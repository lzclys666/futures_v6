#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EG_抓取_期货净持仓.py
因子: EG_POS_NET = 乙二醇期货净持仓

公式: 多头持仓 - 空头持仓（DCE前20名）

当前状态: [✅正常]
- L1: AKShare futures_dce_position_rank(date, vars_list=['EG'])
- L4: db_utils save_l4_fallback
"""
import sys, os, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_pit_dates, ensure_table, save_l4_fallback
import akshare as ak

FACTOR_CODE = "EG_POS_NET"
SYMBOL = "EG"
BOUNDS = (-200000, 200000)

def run():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    # L1: DCE持仓排名
    try:
        print("[L1] AKShare futures_dce_position_rank(vars_list=['EG'])...")
        date_str = obs_date.strftime('%Y%m%d')
        result = ak.futures_dce_position_rank(date=date_str, vars_list=["EG"])
        if result is None:
            raise ValueError("返回None")
        
        # result is a dict: {'eg': DataFrame} or similar
        if isinstance(result, dict):
            df = None
            for key, val in result.items():
                if 'eg' in str(key).lower():
                    df = val
                    break
            if df is None and len(result) > 0:
                df = list(result.values())[0]
        else:
            df = result
        
        if df is None or (hasattr(df, 'empty') and df.empty):
            raise ValueError("Empty DataFrame")
        
        print(f"  Shape: {df.shape}, Columns: {list(df.columns)}")
        print(df.head(3).to_string())
        
        # Try to compute net position from long - short
        # DCE position rank typically has: 名次, 会员简称, 持买仓量, 持买增减, 持卖仓量, 持卖增减
        long_col = None
        short_col = None
        for col in df.columns:
            col_str = str(col)
            if '买' in col_str and '仓' in col_str and '增' not in col_str:
                long_col = col
            elif '卖' in col_str and '仓' in col_str and '增' not in col_str:
                short_col = col
        
        if long_col and short_col:
            total_long = df[long_col].astype(float).sum()
            total_short = df[short_col].astype(float).sum()
            raw_value = total_long - total_short
        else:
            # If columns don't match, try numeric approach
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if len(numeric_cols) >= 2:
                raw_value = float(df[numeric_cols[0]].sum() - df[numeric_cols[1]].sum())
            else:
                raise ValueError(f"无法识别多空列: {list(df.columns)}")
        
        if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
            # Don't skip, still save with warning
        
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0, source='akshare_dce_position_rank')
        print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
        return
    except Exception as e:
        print(f"[L1 FAIL] {type(e).__name__}: {e}")

    # L4
    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date, extra_msg="乙二醇净持仓")

if __name__ == "__main__":
    run()
