#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_美联储联邦基金目标利率.py
因子: AU_FED_RATE = 美联储联邦基金目标利率（%）

公式: 数据采集（无独立计算公式）

当前状态: [✅正常]
- L1: AKShare macro_bank_usa_interest_rate()，source_confidence=1.0
- L2: FRED DFF（联邦基金有效利率），source_confidence=0.9
- L3: save_l4_fallback() 兜底
- bounds: [0.0, 10.0]%（历史区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates
from common.web_utils import fetch_url
from datetime import datetime

FACTOR_CODE = "AU_FED_RATE"
SYMBOL = "AU"
BOUNDS = (0.0, 10.0)


def fetch():
    """L1: AKShare 美联储联邦基金目标利率"""
    print("[L1] AKShare macro_bank_usa_interest_rate()...")
    import akshare as ak
    import pandas as pd
    df = ak.macro_bank_usa_interest_rate()
    if df is None or df.empty:
        raise ValueError("no data")
    col_date = df.columns[1]
    col_val = df.columns[2]
    df = df.dropna(subset=[col_val, col_date])
    df = df.sort_values(col_date)
    latest = df.iloc[-1]
    raw_value = float(latest[col_val])
    obs_date = pd.to_datetime(latest[col_date]).date()
    return raw_value, obs_date


def fetch_l2():
    """L2: FRED DFF（联邦基金有效利率）"""
    print("[L2] FRED DFF...")
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF&vintage_date={today}"
    r_text, err = fetch_url(url, timeout=15)
    if err:
        raise ValueError(f"FRED DFF failed: {err}")
    lines = r_text.strip().split("\n")
    for line in reversed(lines[1:]):
        parts = line.split(",")
        if len(parts) == 2 and parts[1].strip() != ".":
            val = float(parts[1].strip())
            obs_date_str = parts[0].strip()
            if 0 <= val <= 15:
                return val, datetime.strptime(obs_date_str, "%Y-%m-%d").date()
    raise ValueError("FRED DFF: no valid data")


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

    # L2
    if raw_value is None:
        try:
            raw_value, data_obs_date = fetch_l2()
        except Exception as e:
            print(f"[L2] 失败: {e}")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(美联储利率)"):
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
                             extra_msg="(美联储利率)"):
            pass
        else:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None,
                       source="all_sources_failed", source_confidence=0.0)
        return

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, data_obs_date, raw_value,
               source="akshare", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value}% obs={data_obs_date}")


if __name__ == "__main__":
    main()
