#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP_线型低密度聚乙烯-聚丙烯价差.py
因子: PP_SPD_LLDPE_PP = LLDPE-PP期货价差（元/吨）

公式: LLDPE主力合约收盘价 - PP主力合约收盘价

当前状态: [✅正常]
- L1: AKShare futures_main_sina(LLDPE='L0', PP='PP0') → 两个收盘价相减
- L2: 无备源
- L3: save_l4_fallback() DB历史最新值回补

已验证: L0 close=8486, PP0 close=7340, spread=1146
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "PP_SPD_LLDPE_PP"
SYM = "PP"
BOUNDS = (-3000, 5000)  # 价差合理范围（元/吨）


def fetch():
    """获取LLDPE-PP期货价差"""
    # Get LLDPE close
    df_l = ak.futures_main_sina(symbol="L0")
    if df_l is None or len(df_l) == 0:
        raise ValueError("LLDPE data empty")
    latest_l = df_l.sort_values('日期').iloc[-1]
    lldpe_close = float(latest_l['收盘价'])
    lldpe_date = pd.to_datetime(latest_l['日期']).date()

    # Get PP close
    df_p = ak.futures_main_sina(symbol="PP0")
    if df_p is None or len(df_p) == 0:
        raise ValueError("PP data empty")
    latest_p = df_p.sort_values('日期').iloc[-1]
    pp_close = float(latest_p['收盘价'])
    pp_date = pd.to_datetime(latest_p['日期']).date()

    spread = lldpe_close - pp_close
    print(f"  LLDPE={lldpe_close:.0f} ({lldpe_date}), PP={pp_close:.0f} ({pp_date}), spread={spread:.0f}")
    return spread  # 不返回日期，使用get_pit_dates()的obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: futures_main_sina
    try:
        raw_value = fetch()
    except Exception as e:
        print(f"[L1 FAIL] {FCODE}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FCODE}={raw_value:.0f} out of {BOUNDS}, fall back to L4")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return

    save_to_db(FCODE, SYM, pub_date, obs_date, raw_value, source_confidence=1.0, source='AKShare_Sina_L0_PP0')
    print(f"[OK] {FCODE}={raw_value:.0f} obs={obs_date}")


if __name__ == "__main__":
    main()
