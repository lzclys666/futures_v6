#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取期货持仓
因子: 待定义 = 抓取期货持仓

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
"""BR_抓取期货持仓.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, get_latest_value
import akshare as ak

SYMBOL = "BR"

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print("(auto) === BR持仓 === obs={}".format(obs_date))
    try:
        df = ak.futures_main_sina(symbol="BR0")
        if df is not None and len(df) > 0:
            col_map = {str(c).strip(): c for c in df.columns}
            if "持仓量" in col_map:
                val = float(df.iloc[-1][col_map["持仓量"]])
                save_to_db("BR_POS_NET", SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_main_sina")
                print("✅ BR_POS_NET={} 写入成功".format(val))
                return
    except Exception as e:
        print("[L1] 失败: {}".format(e))
    v = get_latest_value("BR_POS_NET", SYMBOL)
    if v is not None:
        save_to_db("BR_POS_NET", SYMBOL, pub_date, obs_date, v, source_confidence=0.5, source="db_回补")
        print("✅ BR_POS_NET={} L4回补成功".format(v))

if __name__ == "__main__":
    main()
