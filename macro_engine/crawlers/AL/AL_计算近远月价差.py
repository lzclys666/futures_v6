#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AL_计算近远月价差.py
因子: AL_SPD_CONTRACT = 沪铝近远月价差（元/吨）

公式: 近月合约收盘价 - 远月合约收盘价（正向市场近月升水，负值代表反向市场）

当前状态: ✅正常
- L1: 新浪nf_实时API（nf_AL0等近远月合约）
- L2: AKShare futures_zh_daily_sina
- bounds: [-500, 500]元/吨（正常近远月价差区间）
- 注: 价差=近月-远月，正数=近月升水（正向市场），负数=近月贴水

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
from common.web_utils import fetch_url
import datetime

FACTOR_CODE = "AL_SPD_CONTRACT"
SYMBOL = "AL"
BOUNDS = (-500, 500)


def get_near_far_codes():
    """生成近月和远月合约代码"""
    today = datetime.date.today()
    months = [1, 3, 5, 7, 9, 11]
    future_months = []
    for y in range(today.year, today.year + 2):
        for mm in months:
            dt = datetime.date(y, mm, 1)
            if dt > today:
                future_months.append((dt, f"AL{str(y)[2:]}{mm:02d}"))
    future_months.sort(key=lambda x: x[0])
    return future_months[:2] if len(future_months) >= 2 else None


def fetch_spread():
    contracts = get_near_far_codes()
    if not contracts:
        print("[ERR] 无法确定合约代码"); return None, None, None
    near_code, far_code = contracts[0][1], contracts[1][1]
    print(f"  近月={near_code}, 远月={far_code}")

    # L1: 新浪
    try:
        print("[L1] 新浪实时API...")
        html, err = fetch_url(
            f"http://hq.sinajs.cn/list=nf_{near_code},nf_{far_code}",
            timeout=10
        )
        if not err and html:
            lines = html.strip().split("\n")
            prices = []
            for line in lines:
                if '"' in line:
                    parts = line.split('"')[1].split(",")
                    if len(parts) >= 5:
                        prices.append(float(parts[4]))
            if len(prices) >= 2:
                spread = round(prices[0] - prices[1], 2)
                if BOUNDS[0] <= spread <= BOUNDS[1]:
                    print(f"[L1] 成功: {spread} 元/吨")
                    return spread, "sina", 0.9
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: AKShare
    try:
        print("[L2] AKShare futures_zh_daily_sina...")
        df1 = ak.futures_zh_daily_sina(symbol=near_code)
        df2 = ak.futures_zh_daily_sina(symbol=far_code)
        if df1 is not None and df2 is not None:
            spread = round(float(df1.iloc[-1]["close"]) - float(df2.iloc[-1]["close"]), 2)
            if BOUNDS[0] <= spread <= BOUNDS[1]:
                print(f"[L2] 成功: {spread} 元/吨")
                return spread, "akshare", 0.9
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
    value, source, confidence = fetch_spread()
    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source=source, source_confidence=confidence)
    else:
        print(f"[ERR] {FACTOR_CODE} 所有数据源均失败")
