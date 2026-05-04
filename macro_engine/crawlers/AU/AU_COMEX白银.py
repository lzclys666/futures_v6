#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_COMEX白银.py
因子: AU_COMEX_AG = COMEX白银期货主力收盘价（美元/盎司）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare futures_main_sina("SI0")，source_confidence=1.0
- L2: 无备选源（COMEX白银仅有SI0主力合约，无次选合约）
- L3: save_l4_fallback() 兜底
- bounds: [10.0, 100.0]美元/盎司（历史区间，2020年后白银大涨曾突破50美元）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
from datetime import datetime
import warnings

FACTOR_CODE = "AU_COMEX_AG"
SYMBOL = "AU"
BOUNDS = (10.0, 100.0)  # COMEX白银历史区间[10, 100]美元/盎司


def fetch():
    """L1: AKShare COMEX白银期货（SI0主力合约）"""
    print("[L1] AKShare futures_main_sina('SI0')...")
    warnings.filterwarnings('ignore')
    import akshare as ak
    df = ak.futures_main_sina(symbol="SI0")
    if df is None or df.empty:
        raise ValueError("no data")
    latest = df.sort_values("日期").iloc[-1]
    # AKShare SI0返回美分/盎司，需除以100转为美元/盎司
    raw_value = float(latest["收盘价"]) / 100.0
    obs_date_str = str(latest["日期"])[:10]
    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d").date()
    print(f"[L1] COMEX_AG=${raw_value} obs={obs_date}")
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

    # L2: 无备选源（COMEX白银仅有SI0主力合约，无次选合约）
    if raw_value is None:
        print("[L2] 无备选源（COMEX白银仅有SI0主力合约，无次选合约）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(COMEX白银)"):
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
                             extra_msg="(COMEX白银)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="COMEX Silver (SI0) via AKShare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={data_obs_date}")


if __name__ == "__main__":
    main()
