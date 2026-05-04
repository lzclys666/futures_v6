#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_CFTC非商业净多.py
因子: AU_CFTC_NC = CFTC黄金非商业净持仓（手）

公式: AU_CFTC_NC = 美元-多头仓位 - 美元-空头仓位

当前状态: [✅正常]
- L1: AKShare macro_usa_cftc_nc_holding()，source_confidence=1.0
- L2: 无备选源（CFTC持仓数据仅通过AKShare聚合，无直接免费API）
- L3: save_l4_fallback() 兜底
- bounds: [-100000, 300000]手（历史区间）

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

FACTOR_CODE = "AU_CFTC_NC"
SYMBOL = "AU"
BOUNDS = (-100000.0, 300000.0)


def fetch():
    """L1: AKShare CFTC黄金非商业净持仓"""
    print("[L1] AKShare macro_usa_cftc_nc_holding()...")
    df = ak.macro_usa_cftc_nc_holding()
    if df is None or df.empty:
        raise ValueError("no data")
    latest = df.sort_values("日期").iloc[-1]
    raw_value = float(latest["美元-净仓位"])
    obs_date = pd.to_datetime(latest["日期"]).date()
    return raw_value, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); return
    print(f"=== {FACTOR_CODE} === obs={obs_date}")

    raw_value, data_obs_date = None, None

    # L1
    try:
        raw_value, data_obs_date = fetch()
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源（CFTC持仓数据仅通过AKShare聚合，无直接免费API）
    if raw_value is None:
        print("[L2] 无备选源（CFTC持仓数据仅通过AKShare聚合，无直接免费API）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(CFTC非商业净多)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
            print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
        return

    # bounds校验
    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(CFTC非商业净多)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="akshare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={data_obs_date}")


if __name__ == "__main__":
    main()
