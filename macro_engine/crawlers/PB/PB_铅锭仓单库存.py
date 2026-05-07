#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PB_铅锭仓单库存.py
因子: PB_STK_WARRANT = 上期所沪铅仓单（吨）

公式: SHFE仓库铅仓单总量（各库房汇总）

当前状态: [✅正常]
- L1: AKShare futures_shfe_warehouse_receipt() → 提取铅仓单汇总
- L4: save_l4_fallback() DB历史最新值回补

数据解释: ROWSTATUS=2 表示全国汇总, WRTWGHTS 为仓单重量(吨)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

FCODE = "PB_STK_WARRANT"
SYM = "PB"
BOUNDS = (1000, 200000)  # 铅仓单合理范围（吨）


def fetch():
    """从SHFE仓单数据中提取铅仓单汇总"""
    wr = ak.futures_shfe_warehouse_receipt()
    if '铅' not in wr:
        raise ValueError(f"futures_shfe_warehouse_receipt 返回的键中无 '铅'，可用键: {list(wr.keys())}")

    df = wr['铅']
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("铅仓单数据为空")

    # ROWSTATUS=2 表示全国汇总行
    total_rows = df[df['ROWSTATUS'] == '2']
    if total_rows.empty:
        raise ValueError("未找到ROWSTATUS=2的汇总行")

    wrt = float(total_rows['WRTWGHTS'].sum())
    return wrt


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FCODE} === pub={pub_date} obs={obs_date}")

    # L1: SHFE warehouse receipt
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

    save_to_db(FCODE, SYM, pub_date, obs_date, raw_value, source_confidence=1.0, source='AKShare_SHFE_warrant')
    print(f"[OK] {FCODE}={raw_value:.0f} obs={obs_date}")


if __name__ == "__main__":
    main()
