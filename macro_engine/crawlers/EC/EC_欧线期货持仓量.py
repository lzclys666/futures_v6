#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
欧线期货持仓量
因子: 待定义 = 欧线期货持仓量

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
sys.path.insert(0, 'd:/futures_v6/macro_engine/crawlers/common')
from db_utils import save_to_db, get_latest_value
import akshare as ak
import pandas as pd

FCODE = "EC_FUT_OI"
SYM = "EC"
EMIN = 1000
EMAX = 100000

def fetch():
    df = ak.futures_main_sina(symbol="EC0")
    if df.empty:
        raise ValueError("EC0 no data")
    # 列: [0]=日期, [1]=开盘, [2]=高, [3]=低, [4]=收盘, [5]=成交量, [6]=持仓, [7]=结算
    latest = df.iloc[-1]
    obs_date = pd.to_datetime(latest.iloc[0]).date()
    raw_value = float(latest.iloc[6])  # 持仓量
    return raw_value, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1] " + FCODE + ": " + str(e))
        latest = get_latest_value(FCODE, SYM)
        if latest is not None:
            print("[L4] " + FCODE + "=" + str(latest))
        else:
            print("[SKIP] " + FCODE)
        return
    if not (EMIN <= raw_value <= EMAX):
        print("[WARN] " + FCODE + "=" + str(raw_value) + " [" + str(EMIN) + "," + str(EMAX) + "]")
        return
    save_to_db(FCODE, SYM, datetime.date.today(), obs_date, raw_value, source_confidence=1.0)
    print("[OK] " + FCODE + "=" + str(raw_value) + " obs=" + str(obs_date))

if __name__ == "__main__":
    main()
