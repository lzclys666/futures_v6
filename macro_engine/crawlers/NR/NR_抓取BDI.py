#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取BDI
因子: NR_FREIGHT_BDI = 抓取BDI

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak
import pandas as pd

FACTOR_CODE = "NR_FREIGHT_BDI"
SYMBOL = "NR"


def fetch_bdi(obs_date):
    """
    获取BDI指数。L1优先，失败则L4回补。
    返回: (value, source_str) 或 (None, None)
    """
    # L1: AKShare宏观航运BDI
    try:
        df = ak.macro_shipping_bdi()
        if df is not None and len(df) > 0 and "日期" in df.columns and "最新值" in df.columns:
            df["日期"] = pd.to_datetime(df["日期"])
            df = df.sort_values("日期", ascending=False)
            # 找obs_date之前最近交易日
            target = pd.Timestamp(obs_date)
            candidates = df[df["日期"] <= target]
            if len(candidates) > 0:
                row = candidates.iloc[0]
                bdi_val = float(row["最新值"])
                if 200 <= bdi_val <= 15000:  # BDI历史极值范围
                    date_str = row["日期"].strftime("%Y-%m-%d")
                    print(f"  [L1] BDI={bdi_val} (数据日期={date_str})")
                    return bdi_val, "akshare_macro_shipping_bdi"
    except Exception as e:
        print(f"  [L1] BDI获取失败: {e}")

    # L4: 数据库回补
    print("  [L4] 尝试数据库回补...")
    val = get_latest_value(FACTOR_CODE, SYMBOL)
    if val is not None and 200 <= val <= 15000:
        print(f"  [L4] 回补值: {val}")
        return val, "db_回补"

    print("  [FAIL] BDI无数据")
    return None, None


def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} (波罗的海干散货指数) === obs={obs_date}")

    val, src = fetch_bdi(obs_date)

    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source=src)
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
    else:
        print(f"[FAIL] {FACTOR_CODE}: 无数据")

    return 0 if val is not None else 1


if __name__ == "__main__":
    sys.exit(main())
