#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_US_CPI.py
因子: AU_US_CPI_YOY = 美国CPI同比增速（%）

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- 数据源: AKShare macro_usa_cpi_yoy()，L1权威（BLS数据）
- 采集逻辑: 取'现值'列最新非空行（已是同比值）
- obs_date: 数据发布日期
- bounds: [-2.0, 15.0]%（历史区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

from datetime import datetime
import functools
print_enc = functools.partial(print, flush=True)

FACTOR_CODE = "AU_US_CPI_YOY"
SYMBOL = "AU"
BOUNDS = (-2.0, 15.0)


def fetch():
    """L1: AKShare 美国CPI同比（BLS via AKShare）"""
    print_enc("[L1] AKShare macro_usa_cpi_yoy()...")
    import warnings; warnings.filterwarnings('ignore')
    import akshare as ak
    df = ak.macro_usa_cpi_yoy()
    if df is None or df.empty:
        raise ValueError("no data")
    df = df[df["现值"].notna()]
    if df.empty:
        raise ValueError("all CPI values are NaN")
    df = df.sort_values("发布日期", ascending=False)
    latest = df.iloc[0]
    raw_value = float(latest["现值"])
    obs_date_str = str(latest["发布日期"])[:10]
    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d").date()
    print_enc(f"[L1] CPI={raw_value}% obs={obs_date}")
    return raw_value, obs_date


if __name__ == "__main__":
    import warnings; warnings.filterwarnings('ignore')
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")
        val = get_latest_value(FACTOR_CODE, SYMBOL)
        if val is not None:
            print(f"[L4] 兜底: {val}")
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val,
                       source="db_回补", source_confidence=0.5)
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source="BLS via AKShare", source_confidence=0.9)
    print(f"[OK] {FACTOR_CODE}={raw_value}% obs={obs_date}")
