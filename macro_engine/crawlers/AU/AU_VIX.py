#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AU_VIX.py
因子: AU_VIX = CBOE VIX恐慌指数

公式: 数据采集（无独立计算公式）

当前状态: ✅正常
- 数据源: FRED VIXCLS (fred.stlouisfed.org)，L1权威
- 采集逻辑: 直接请求FRED CSV，取最新非空收盘价
- obs_date: 数据日期
- bounds: [5.0, 80.0]（历史区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import requests
from datetime import datetime
import functools
print_enc = functools.partial(print, flush=True)

FACTOR_CODE = "AU_VIX"
SYMBOL = "AU"
BOUNDS = (5.0, 80.0)


def fetch():
    """L1: FRED VIXCLS 直接CSV接口"""
    print_enc("[L1] FRED VIXCLS...")
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        raise ValueError(f"FRED status={r.status_code}")
    lines = r.text.strip().split("\n")
    if len(lines) < 2:
        raise ValueError("FRED VIX: empty data")
    last_line = lines[-1]
    parts = last_line.split(",")
    obs_date_str = parts[0]
    raw_value = float(parts[1])
    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d").date()
    print_enc(f"[L1] VIX={raw_value} obs={obs_date}")
    return raw_value, obs_date


if __name__ == "__main__":
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
               source="FRED VIXCLS (CBOE VIX)", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
