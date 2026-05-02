#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取仓单
因子: sa_warrant_daily = 抓取仓单

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
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

FACTOR_CODE = "sa_warrant_daily"
SYMBOL = "SA"

def fetch():
    import pandas as pd
    print("[L1] AKShare futures_warehouse_receipt_czce SA...")
    try:
        data = ak.futures_warehouse_receipt_czce()
        if "SA" in data:
            df = data["SA"]
            # 取总计行（�ֿ�编号为NaN或总计关键词）
            total_row = None
            for _, row in df.iterrows():
                if pd.isna(row.iloc[0]) or "合计" in str(row.iloc[0]) or "总计" in str(row.iloc[0]):
                    total_row = row
                    break
            if total_row is not None:
                # 取"注册仓单"列（第4列，index=3）或"总注册仓单"列
                for i, col in enumerate(df.columns):
                    if "注册" in str(col) or "仓单" in str(col):
                        val = total_row.iloc[i]
                        if pd.notna(val):
                            val = float(str(val).replace(",", ""))
                            print(f"[L1] SA仓单: {val} 吨 ({df.columns[i]})")
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
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_czce_warehouse")
        print(f"✅ {FACTOR_CODE}={val} 写入成功")
    else:
        print("[L4] DB回补...")
        ok = save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
        if ok:
            print(f"[OK] {FACTOR_CODE} L4回补成功")
        else:
            print(f"[SKIP] {FACTOR_CODE} 今日已有数据或无历史值")

if __name__ == "__main__":
    main()
