#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SN_娌敗鏈熻揣鏀剁洏浠?py
鍥犲瓙: SN_FUT_CLOSE = 娌敗鏈熻揣涓诲姏鍚堢害鏀剁洏浠?
鍏紡: SN_FUT_CLOSE = SN0涓诲姏鍚堢害鏃ユ敹鐩樹环锛堝厓/鍚級

褰撳墠鐘舵€? [鉁呮甯竇
- L1: AKShare futures_main_sina(symbol="SN0")
- L4: save_l4_fallback() DB鍘嗗彶鏈€鏂板€煎洖琛?- L5: 涓嶅啓NULL鍗犱綅绗?"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..'))
from common.db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "SN_FUT_CLOSE"
SYM = "SN"
BOUNDS = (150000, 500000)


def fetch():
    df = ak.futures_main_sina(symbol="SN0")
    if df.empty:
        raise ValueError("no data")
    latest = df.sort_values('鏃ユ湡').iloc[-1]
    return float(latest['鏀剁洏浠?]), pd.to_datetime(latest['鏃ユ湡']).date()


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print(f"[L1] {FCODE}: {e}")
        save_l4_fallback(FCODE, SYM, pub_date, obs_date)
        return
    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FCODE}={raw_value} out of {BOUNDS}")
        return
    save_to_db(FCODE, SYM, pub_date, obs_date, raw_value, source_confidence=1.0, source='AKShare_Sina_SN0')
    print(f"[OK] {FCODE}={raw_value} obs={obs_date}")


if __name__ == "__main__":
    main()
