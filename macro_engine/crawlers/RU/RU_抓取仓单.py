#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取仓单
因子: 待定义 = 抓取仓单

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
import pandas as pd

SYMBOL = "RU"

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print("(auto) === RU仓单 === obs={}".format(obs_date))
    try:
        data = ak.futures_warehouse_receipt_czce()
        if "RU" in data:
            df = data["RU"]
            for _, row in df.iterrows():
                if pd.isna(row.iloc[0]) or "\u5408\u8ba1" in str(row.iloc[0]):
                    for i, col in enumerate(df.columns):
                        if "\u6ce8\u518c" in str(col) or "\u4ed3\u5355" in str(col) or "\u603b" in str(col):
                            val = row.iloc[i]
                            if pd.notna(val):
                                val = float(str(val).replace(",", ""))
                                save_to_db("RU_INV_QINGDAO", SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_czce_warehouse")
                                print(">>> RU_INV_QINGDAO={} 写入成功".format(val))
                                return
    except Exception as e:
        print("[L1] 失败: {}".format(e))
    v = get_latest_value("RU_INV_QINGDAO", SYMBOL)
    if v is not None:
        save_to_db("RU_INV_QINGDAO", SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
        print(">>> RU_INV_QINGDAO={} L4回补成功".format(v))

if __name__ == "__main__":
    main()
