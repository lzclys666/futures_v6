#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取期货持仓
因子: 待定义 = 抓取期货持仓

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

SYMBOL = "RU"

def main():
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print("(auto) === RU持仓 === obs={}".format(obs_date))
    try:
        df = ak.futures_main_sina(symbol="RU0")
        if df is not None and len(df) > 0:
            col_map = {str(c).strip(): c for c in df.columns}
            if "持仓量" in col_map:
                val = float(df.iloc[-1][col_map["持仓量"]])
                save_to_db("RU_POS_NET", SYMBOL, pub_date, obs_date, val, source_confidence=1.0, source="akshare_futures_main_sina")
                print(">>> RU_POS_NET={} 写入成功".format(val))
                return
    except Exception as e:
        print("[L1] 失败: {}".format(e))
    save_l4_fallback("\1", SYMBOL, pub_date, obs_date)

if __name__ == "__main__":
    main()
