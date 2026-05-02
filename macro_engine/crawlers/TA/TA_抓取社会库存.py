#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取社会库存
因子: 待定义 = 抓取社会库存

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

SYMBOL = "TA"

def fetch():
    print("[L1] AKShare futures_inventory_em PTA...")
    try:
        df = ak.futures_inventory_em(symbol="PTA")
        if df is not None and len(df) > 0:
            row = df.iloc[-1]
            val = float(row.iloc[1])
            print(f"[L1] PTA库存={val}")
            return val
    except Exception as e:
        print(f"[L1] 失败: {e}")
    return None

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === TA库存/有效预报 === obs={obs_date}")
    val = fetch()
    if val is not None:
        # TA_STK_SOCIAL = PTA社会库存（百川/隆众）
        save_to_db("TA_STK_SOCIAL", SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_inventory_em")
        print(f"[OK] TA_STK_SOCIAL={val} 写入成功")
    else:
        # TA_STK_WARRANT 不在此脚本处理（由TA_抓取郑商所仓单.py负责）
        for fc in ["TA_STK_SOCIAL"]:
            v = get_latest_value(fc, SYMBOL)
            if v is not None:
                save_to_db(fc, SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
                print(f"[OK] {fc}={v} L4回补成功")

if __name__ == "__main__":
    main()
