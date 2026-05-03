#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取近月合约价
因子: sa_futures_near_price = 抓取近月合约价

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

FACTOR_CODE = "sa_futures_near_price"
SYMBOL = "SA"

def fetch(obs_date):
    print("[L1] AKShare futures_spot_price near_contract...")
    date_str = obs_date.strftime("%Y%m%d")
    df = ak.futures_spot_price(date=date_str, vars_list=["SA"])
    if df is not None and not df.empty:
        row = df.iloc[-1]
        if "near_contract_price" in row and pd.notna(row["near_contract_price"]):
            val = float(row["near_contract_price"])
            contract = str(row.get("near_contract", ""))
            print(f"[L1] SA近月合约={contract} 价格={val}")
            return val
    # 备选：futures_main_sina
    print("[L2] 备选futures_main_sina...")
    df2 = ak.futures_main_sina(symbol="SA0")
    if df2 is not None and len(df2) > 0:
        for c in df2.columns:
            if str(c).strip() in ("最新", "收盘"):
                val = float(df2.iloc[-1][c])
                print(f"[L2] SA近月={val}")
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
