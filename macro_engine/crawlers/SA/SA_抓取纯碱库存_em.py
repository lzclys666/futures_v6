#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取纯碱库存_em
因子: sa_inventory_w = 抓取纯碱库存_em

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

FACTOR_CODE = "sa_inventory_w"
SYMBOL = "SA"

def fetch():
    print("[L1] AKShare futures_inventory_em(纯碱)...")
    try:
        df = ak.futures_inventory_em(symbol="纯碱")
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            val = float(row.iloc[1])  # 今日库存
            print(f"[L1] SA纯碱库存: {val} 吨  (日变化: {row.iloc[2]})")
            return val
    except Exception as e:
        print(f"[L1] 失败: {e}")
    return None

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === {FACTOR_CODE} === obs={obs_date}")
    val = fetch()
    if val is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_inventory_em")
        print(f"[OK] {FACTOR_CODE}={val} 写入成功")
    else:
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")

if __name__ == "__main__":
    main()
