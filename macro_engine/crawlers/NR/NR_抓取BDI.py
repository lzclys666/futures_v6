#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NR_抓取BDI.py
因子: NR_FREIGHT_BDI = 波罗的海干散货指数(BDI)

公式: NR_FREIGHT_BDI = BDI指数（点）

当前状态: [✅正常]
- L1: AKShare macro_shipping_bdi() — 航运BDI指数
- L2: 无备源
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FACTOR_CODE = "NR_FREIGHT_BDI"
SYMBOL = "NR"
BOUNDS = (200, 15000)


def fetch_bdi(obs_date):
    """获取BDI指数"""
    try:
        df = ak.macro_shipping_bdi()
        if df is not None and len(df) > 0 and "日期" in df.columns and "最新值" in df.columns:
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values("日期", ascending=False)
            target = pd.Timestamp(obs_date)
            candidates = df[df["日期"] <= target]
            if len(candidates) > 0:
                row = candidates.iloc[0]
                bdi_val = float(row["最新值"])
                if BOUNDS[0] <= bdi_val <= BOUNDS[1]:
                    date_str = row["日期"].strftime("%Y-%m-%d")
                    print(f"  [L1] BDI={bdi_val} (数据日期={date_str})")
                    return bdi_val, "akshare_macro_shipping_bdi"
    except Exception as e:
        print(f"  [L1] BDI获取失败: {e}")
    return None, None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    val, src = fetch_bdi(obs_date)

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source=src)
        print(f"[OK] {FACTOR_CODE}={val} obs={obs_date}")
    else:
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
