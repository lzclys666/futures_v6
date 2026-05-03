#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取期货日行情
因子: 待定义 = 抓取期货日行情

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

FACTORS = [
    ("sa_futures_daily_close", "收盘价"),
    ("sa_futures_daily_hold", "持仓量"),
]
SYMBOL = "SA"

def fetch():
    print("[L1] AKShare futures_main_sina SA0...")
    df = ak.futures_main_sina(symbol="SA0")
    if df is None or len(df) == 0:
        return {}
    # 列名: 日期, 昨收, 开盘, 最高, 最低, 最新, 成交量, 持仓量, 结算
    col_map = {}
    for c in df.columns:
        cn = str(c).strip()
        if cn == "日期": col_map["date"] = c
        elif cn in ("最新", "收盘"): col_map["close"] = c
        elif cn == "持仓量": col_map["oi"] = c
        elif cn == "成交量": col_map["vol"] = c
    row = df.iloc[-1]
    result = {}
    if "close" in col_map:
        result["sa_futures_daily_close"] = float(row[col_map["close"]])
    if "oi" in col_map:
        result["sa_futures_daily_hold"] = float(row[col_map["oi"]])
    for k, v in result.items():
        print(f"[L1] {k}={v}")
    return result

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === SA期货日行情 === obs={obs_date}")
    vals = fetch()
    for fc, val in vals.items():
        save_to_db(fc, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_main_sina")
        print(f"[OK] {fc}={val} 写入成功")
    if not vals:
        print(f"[L4] 无数据，尝试L4回补...")
        for fc, _ in FACTORS:
            ok = save_l4_fallback(fc, SYMBOL, pub_date, obs_date)
            if ok:
                print(f"[OK] {fc} L4回补成功")
            else:
                print(f"[SKIP] {fc} 今日已有数据或无历史值")

if __name__ == "__main__":
    main()
