#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_计算铝铜比价.py
因子: AL_SPD_AL_CU = 沪铝/沪铜价格比

公式: 比价 = AL0收盘价 / CU0收盘价（无量纲）

当前状态: ✅正常
- L1: 新浪nf_AL0/nf_CU0实时行情
- L2: AKShare futures_zh_daily_sina
- bounds: [0.1, 1.0]（铝价远低于铜价，正常区间0.2~0.5）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import requests

FACTOR_CODE = "AL_SPD_AL_CU"
SYMBOL = "AL"
BOUNDS = (0.1, 1.0)


def fetch_ratio():
    # L1: 新浪
    try:
        print("[L1] 新浪 nf_AL0 & nf_CU0...")
        resp = requests.get(
            "http://hq.sinajs.cn/list=nf_AL0,nf_CU0",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        resp.encoding = "gbk"
        if resp.status_code == 200 and resp.text:
            lines = resp.text.strip().split("\n")
            prices = []
            for line in lines:
                if '"' in line:
                    parts = line.split('"')[1].split(",")
                    if len(parts) >= 5:
                        prices.append(float(parts[4]))
            if len(prices) >= 2 and prices[1] > 0:
                ratio = round(prices[0] / prices[1], 4)
                if BOUNDS[0] <= ratio <= BOUNDS[1]:
                    print(f"[L1] 成功: AL/CU={ratio} (AL={prices[0]:.0f}, CU={prices[1]:.0f})")
                    return ratio, "sina", 0.9
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: AKShare
    try:
        print("[L2] AKShare futures_zh_daily_sina...")
        df_al = ak.futures_zh_daily_sina(symbol="AL0")
        df_cu = ak.futures_zh_daily_sina(symbol="CU0")
        if df_al is not None and df_cu is not None:
            p_al = float(df_al.iloc[-1]["close"])
            p_cu = float(df_cu.iloc[-1]["close"])
            if p_cu > 0:
                ratio = round(p_al / p_cu, 4)
                if BOUNDS[0] <= ratio <= BOUNDS[1]:
                    print(f"[L2] 成功: AL/CU={ratio}")
                    return ratio, "akshare", 0.9
    except Exception as e:
        print(f"[L2] 失败: {e}")

    # L4回补
    print("[L4] DB历史回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None:
        print(f"[L4] 兜底: {val}")
        return val, "db_回补", 0.5
    return None, None, None


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日"); exit(0)
    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")
    value, source, confidence = fetch_ratio()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source=source, source_confidence=confidence)
    else:
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
