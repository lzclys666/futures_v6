#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HC_热轧卷板期货收盘价
因子: HC_FUT_CLOSE = 热轧卷板期货收盘价

公式: 无（直接采集AKShare HC0主力合约收盘价）

当前状态: [正常]
- L1: AKShare futures_main_sina(HC0) 主力合约收盘价
- L4: save_l4_fallback 历史回补
"""
import sys, os, datetime

if os.name == "nt":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback

try:
    import akshare as ak
    HAS_AK = True
except ImportError:
    HAS_AK = False

FACTOR_CODE = "HC_FUT_CLOSE"
SYMBOL = "HC"
BOUNDS = (1000, 10000)  # 热轧卷板期货价格范围（元/吨）

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    sys.stdout.write(f"(auto) === {FACTOR_CODE} === obs={obs_date}\n")
    sys.stdout.flush()

    if not HAS_AK:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date):
            return 0
        else:
            sys.stdout.write("[WARN] All sources failed\n")
            return 0

    try:
        df = ak.futures_main_sina(symbol="HC0")
        if df is None or df.empty:
            raise ValueError("Empty DataFrame")
        df = df.dropna(subset=['收盘价'])
        latest = df.iloc[-1]
        date_str = str(latest['日期'])[:10]
        close = float(latest['收盘价'])
        fetched_obs = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        if not (BOUNDS[0] <= close <= BOUNDS[1]):
            sys.stdout.write(f"[WARN] {FACTOR_CODE}={close} out of {BOUNDS}\n")
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, fetched_obs, close,
                   source_confidence=1.0, source="AKShare futures_main_sina HC0")
        sys.stdout.write(f"[L1] {FACTOR_CODE}={close} ({fetched_obs}) done\n")
        return 0
    except Exception as e:
        sys.stderr.write(f"[L1] AKShare HC0 failed: {e}\n")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date):
            return 0
        else:
            sys.stdout.write("[WARN] All sources failed\n")
            return 0

if __name__ == "__main__":
    sys.exit(main())
