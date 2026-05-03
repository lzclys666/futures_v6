#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取次月合约价
因子: sa_futures_sub_daily_close = 抓取次月合约价

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
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback, get_latest_value
import akshare as ak
import pandas as pd

FACTOR_CODE = "sa_futures_sub_daily_close"
SYMBOL = "SA"

def fetch(obs_date):
    print("[L1] AKShare futures_spot_price dominant...")
    date_str = obs_date.strftime("%Y%m%d")
    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])
    if df is not None and not df.empty:
        row = df.iloc[-1]
        if "dominant_contract_price" in row and pd.notna(row["dominant_contract_price"]):
            val = float(row["dominant_contract_price"])
            print(f"[L1] SA主力合约价格={val}")
            return val
    return None

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    val = fetch(obs_date)
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_spot_price")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
    else:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if not ok:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")

if __name__ == "__main__":
    main()
