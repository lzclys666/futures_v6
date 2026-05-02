#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BR_计算比价.py
因子: BR_SPD_RU_BR = 顺丁橡胶/天然橡胶现货比价

公式: BR_SPD_RU_BR = BR现货价 / RU现货价

当前状态: ✅正常
- 数据源: AKShare futures_spot_price(date, vars_list=['BR', 'RU'])，L1权威
- 采集逻辑: 取最近交易日BR和RU的spot_price相除
- obs_date: 数据实际日期
- bounds: [0.5, 1.5]（橡胶比价历史区间）

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd
from datetime import timedelta

FACTOR_CODE = "BR_SPD_RU_BR"
SYMBOL = "BR"
BOUNDS = (0.5, 1.5)


def fetch(obs_date):
    """L1: AKShare BR/RU现货价比"""
    print("[L1] AKShare futures_spot_price(vars_list=['BR','RU'])...")
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime("%Y%m%d")
        try:
            df = ak.futures_spot_price(date=date_str, vars_list=["BR", "RU"])
            if df is None or df.empty:
                continue
            br_row = df[df["symbol"] == "BR"]
            ru_row = df[df["symbol"] == "RU"]
            if br_row.empty or ru_row.empty:
                continue
            br_price = float(br_row.iloc[-1]["spot_price"])
            ru_price = float(ru_row.iloc[-1]["spot_price"])
            if br_price <= 0 or ru_price <= 0:
                continue
            actual_date = pd.to_datetime(br_row.iloc[-1]["date"]).date()
            raw_value = round(br_price / ru_price, 4)
            print(f"[L1] BR={br_price} RU={ru_price} ratio={raw_value}")
            return raw_value, actual_date
        except Exception as e:
            print(f"[L1] {date_str}: {e}")
    return None, None


if __name__ == "__main__":
    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value, actual_date = fetch(obs_date)
    except Exception as e:
        print(f"[L1] 失败: {e}")
        raw_value = None

    if raw_value is None:
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

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date, raw_value,
               source="akshare_futures_spot_price", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={actual_date}")
