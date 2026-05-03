#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AG_抓取期货日行情.py
因子: AG_FUT_CLOSE = 沪银期货收盘价（元/千克）
       AG_POS_NET = 沪银期货持仓量（手）

公式: 数据采集（无独立计算公式）

当前状态: [OK] 正常
- AKShare futures_main_sina("AG0") 返回沪银主力合约完整行情
- 收盘价提取 "收盘" 字段，写入 AG_FUT_CLOSE
- 持仓量提取 "持仓量" 字段，写入 AG_POS_NET
- 数据源: L1 AKShare新浪期货接口
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

SYMBOL = "AG"


def fetch():
    print("[L1] AKShare futures_main_sina AG0...")
    df = ak.futures_main_sina(symbol="AG0")
    if df is None or len(df) == 0:
        return {}
    col_map = {str(c).strip(): c for c in df.columns}
    row = df.iloc[-1]
    result = {}
    # 收盘价
    for close_name in ["收盘价", "最新价", "昨收"]:
        if close_name in col_map:
            val = float(row[col_map[close_name]])
            result["AG_FUT_CLOSE"] = val
            print(f"[L1] AG收盘价={val}")
            break
    # 持仓量
    if "持仓量" in col_map:
        val = float(row[col_map["持仓量"]])
        result["AG_POS_NET"] = val
        print(f"[L1] AG持仓量={val}")
    return result


def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === AG期货日行情 === obs={obs_date}")
    vals = fetch()
    for fc, val in vals.items():
        save_to_db(fc, SYMBOL, pub_date, obs_date, val,
                   source_confidence=1.0, source="akshare_futures_main_sina")
        print(f"[OK] {fc}={val} 写入成功")
    if not vals:
        v = get_latest_value("AG_POS_NET", SYMBOL)
        if v is not None:
            save_to_db("AG_POS_NET", SYMBOL, pub_date, obs_date, v,
                       source_confidence=0.5, source="db_回补")
            print(f"[OK] AG_POS_NET={v} L4回补成功")


if __name__ == "__main__":
    main()
