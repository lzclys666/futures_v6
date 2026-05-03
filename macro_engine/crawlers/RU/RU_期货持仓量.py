#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货持仓量
因子: RU_FUT_OI = 期货持仓量

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
from common.db_utils import save_to_db, get_pit_dates
from common.io_win import fix_encoding
import akshare as ak
import warnings
warnings.filterwarnings('ignore')

FACTOR_CODE = "RU_FUT_OI"
SYMBOL = "RU"

def fetch(obs_date):
    print(f"[L1] AKShare futures_main_sina RU0 obs={obs_date}...")
    try:
        df = ak.futures_main_sina(symbol="RU0")
        if df is not None and len(df) > 0:
            # 找最新一行 (按日期)
            df.columns = ['date','open','high','low','close','volume','open_interest','settle']
            df = df.sort_values('date')
            row = df.iloc[-1]
            val = float(row['open_interest'])
            print(f"[L1] RU持仓量: {val} (obs={row['date']})")
            return val, "akshare_futures_main_sina", 1.0
    except Exception as e:
        print(f"[L1] Error: {e}")
    return None, None, None

def main():
    import argparse
    auto = "--auto" in sys.argv
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === obs={obs_date}")
    val, src, conf = fetch(obs_date)
    if val is not None:
        # RU_FUT_OI 和 RU_INV_TOTAL 共用持仓量数据
        for fc in [FACTOR_CODE, "RU_INV_TOTAL"]:
            save_to_db(fc, SYMBOL, pub_date, obs_date, val, src, conf)
            print(f"[OK] {fc}={val} 写入成功")
    else:
        print(f"[L4] 回补...")
        from common.db_utils import get_latest_value
        v = get_latest_value(FACTOR_CODE, SYMBOL)
        if v is not None:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, v, source="db_回补", source_confidence=0.5)
            print(f"[OK] {FACTOR_CODE}={v} L4回补成功")
        else:
            # Null 占位写入
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, None, source="all_sources_failed", source_confidence=0.0)
            print(f"[DB] 因子 {FACTOR_CODE} NULL 占位写入")

if __name__ == "__main__":
    fix_encoding()
    main()
