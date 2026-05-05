#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青期货仓单.py
因子: BU_STK_WARRANT = 沥青期货仓单（吨）

公式: SHFE仓单数据中石油沥青品种的WRTWGHTS合计

当前状态: [✅正常]
- L1: AKShare futures_shfe_warehouse_receipt()，过滤石油沥青品种，求和WRTWGHTS
- L2: 无备选源（SHFE仓单仅有此API）
- L3: save_l4_fallback() 兜底
- bounds: [0, 1000000]吨（2026-05实测764070吨）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "BU_STK_WARRANT"
SYMBOL = "BU"
BOUNDS = (0.0, 1000000.0)  # 吨（2026-05实测764070吨，11个厂库合计）


def fetch():
    """L1: AKShare SHFE仓单数据，过滤沥青品种"""
    print("[L1] AKShare futures_shfe_warehouse_receipt()...")
    result = ak.futures_shfe_warehouse_receipt()
    if not isinstance(result, dict) or len(result) == 0:
        raise ValueError("SHFE仓单数据为空")

    # 查找石油沥青品种的key
    bu_key = None
    for k in result.keys():
        if '沥青' in k or '石油' in k:
            bu_key = k
            break

    if bu_key is None:
        # 尝试模糊匹配
        for k in result.keys():
            if 'BU' in k.upper():
                bu_key = k
                break

    if bu_key is None:
        available = list(result.keys())
        raise ValueError(f"SHFE仓单数据中无沥青品种，可用品种: {available}")

    df = result[bu_key]
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError(f"沥青仓单数据为空 (key={bu_key})")

    total = float(pd.to_numeric(df['WRTWGHTS'], errors='coerce').sum())
    print(f"[L1] 沥青仓单: {total:.0f}吨 (key={bu_key}, {len(df)}行)")
    return total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    raw_value = None

    # L1
    try:
        raw_value = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源
    if raw_value is None:
        print("[L2] 无备选源（SHFE仓单仅有futures_shfe_warehouse_receipt）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青仓单)"):
            pass
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青仓单)"):
            pass
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source="akshare_futures_shfe_warehouse_receipt", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value:.0f}吨")
