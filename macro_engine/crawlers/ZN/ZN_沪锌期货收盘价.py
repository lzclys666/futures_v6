#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪锌期货收盘价
因子: 待定义 = 沪锌期货收盘价

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date
import pandas as pd

FCODE = "ZN_FUT_CLOSE"
SYM = "ZN"
EMIN = 15000
EMAX = 35000

def fetch():
    df = ak.futures_main_sina(symbol="ZN0")
    if df.empty:
        raise ValueError("no data")
    latest = df.sort_values('日期').iloc[-1]
    return float(latest['收盘价']), pd.to_datetime(latest['日期']).date()

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1] " + FCODE + ": " + str(e))
        latest = get_latest_value(FCODE, SYM)
        if latest is not None:
            print("[L4FB] " + FCODE + "=" + str(latest))
            return
        print("[SKIP] " + FCODE + ": no data")
        return
    if not (EMIN <= raw_value <= EMAX):
        print("[WARN] " + FCODE + "=" + str(raw_value) + " out of [" + str(EMIN) + "," + str(EMAX) + "]")
        return
    save_to_db(FCODE, SYM, date.today(), obs_date, raw_value, source_confidence=1.0)
    print("[OK] " + FCODE + "=" + str(raw_value) + " obs=" + str(obs_date))

if __name__ == "__main__":
    main()
