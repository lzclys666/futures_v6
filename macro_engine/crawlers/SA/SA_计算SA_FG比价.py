#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算SA_FG比价
因子: 待定义 = 计算SA_FG比价

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
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd

SYMBOL = "SA"

def fetch(obs_date):
    print("[L1] AKShare futures_spot_price(SA+FG)...")
    date_str = obs_date.strftime("%Y%m%d")
    df = ak.futures_spot_price(date=date_str, vars_list=["SA", "FG"])
    if df is None or len(df) == 0:
        return {}
    result = {}
    row_sa = df[df["symbol"] == "SA"]
    row_fg = df[df["symbol"] == "FG"]
    if len(row_sa) and len(row_fg):
        sa_price = float(row_sa.iloc[-1]["spot_price"])
        fg_price = float(row_fg.iloc[-1]["spot_price"])
        if sa_price > 0 and fg_price > 0:
            ratio_spot = sa_price / fg_price
            ratio_fut = float(row_sa.iloc[-1]["near_contract_price"]) / float(row_fg.iloc[-1]["near_contract_price"]) \
                if pd.notna(row_sa.iloc[-1]["near_contract_price"]) and pd.notna(row_fg.iloc[-1]["near_contract_price"]) else None
            result["sa_ratio_glass"] = round(ratio_spot, 4)
            print(f"[L1] SA/FG现货比价={ratio_spot:.4f}")
            if ratio_fut:
                result["sa_ratio_glass_futures"] = round(ratio_fut, 4)
                print(f"[L1] SA/FG期货比价={ratio_fut:.4f}")
    return result

def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === SA_FG比价 === obs={obs_date}")
    vals = fetch(obs_date)
    for fc, val in vals.items():
        save_to_db(fc, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_spot_price")
        print(f"[OK] {fc}={val} 写入成功")
    if not vals:
        for fc in ["sa_ratio_glass", "sa_ratio_glass_futures"]:
            ok = save_l4_fallback(fc, SYMBOL, pub_date, obs_date)
            if ok:
                print(f"[OK] {fc} L4回补成功")
            else:
                print(f"[SKIP] {fc} 今日已有数据或无历史值")

if __name__ == "__main__":
    main()
