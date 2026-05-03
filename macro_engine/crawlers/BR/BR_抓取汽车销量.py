#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BR_抓取汽车销量.py
因子: BR_DEM_AUTO = 中国汽车销量（万辆/月）

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 数据源: AKShare car_market_total_cpca(symbol='狭义乘用车', indicator='销量')，当前返回空
- 尝试过的数据源: car_market_total_cpca（空DataFrame）
- 解决方案: 需寻找替代数据源或确认API恢复时间

订阅优先级: ★★★
替代付费源: 中国汽车工业协会（月度发布）/ 卓创资讯 / 隆众资讯
"""
import sys, os as _os
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value

import akshare as ak
import pandas as pd
import re

FACTOR_CODE = "BR_DEM_AUTO"
SYMBOL = "BR"
BOUNDS = (50.0, 500.0)


def fetch():
    """L1: AKShare 狭义乘用车销量"""
    print("[L1] AKShare car_market_total_cpca(symbol='狭义乘用车', indicator='销量')...")
    import warnings; warnings.filterwarnings('ignore')
    df = ak.car_market_total_cpca(symbol="狭义乘用车", indicator="销量")
    if df is None or df.empty:
        raise ValueError("API返回空数据")
    df.columns = ["month", "prev_year", "curr_year"]
    df = df.dropna(subset=["curr_year"])
    if df.empty:
        raise ValueError("无有效销量数据")
    latest = df.iloc[-1]
    raw_value = float(latest["curr_year"])
    # 解析 "2025年12月" -> 月末日期
    m = re.search(r"(\d{4})年(\d+)月", str(latest["month"]))
    if m:
        from calendar import monthrange
        year, month = int(m.group(1)), int(m.group(2))
        last_day = monthrange(year, month)[1]
        obs_date = pd.Timestamp(year, month, last_day).date()
    else:
        raise ValueError(f"无法解析月份: {latest['month']}")
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
               source="中汽协 via AKShare", source_confidence=0.9)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
