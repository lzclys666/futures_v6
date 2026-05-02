#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取PTA库存
因子: TA_STK_SOCIAL = 抓取PTA库存

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
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

FACTOR_CODE = "TA_STK_SOCIAL"
SYMBOL = "TA"

def fetch():
    print("[L1] AKShare futures_inventory_em PTA...")
    try:
        df = ak.futures_inventory_em(symbol="PTA")
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            val = float(row.iloc[1])
            print(f"[L1] PTA库存: {val} 吨")
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
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")
        else:
            print(f"[WARN]️  {FACTOR_CODE} 无数据源")

if __name__ == "__main__":
    main()
