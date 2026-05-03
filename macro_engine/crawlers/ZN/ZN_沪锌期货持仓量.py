#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沪锌期货持仓量
因子: 待定义 = 沪锌期货持仓量

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

FCODE = "ZN_FUT_OI"
SYM = "ZN"
EMIN = 50000
EMAX = 400000

def fetch():
    df = ak.futures_main_sina(symbol="ZN0")
    if df.empty:
        raise ValueError("no data")
    latest = df.sort_values('日期').iloc[-1]
    oi_val = float(latest.get('持仓量', 0))
    obs = pd.to_datetime(latest['日期']).date()
    return oi_val, obs

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
    save_to_db(FCODE, SYM, date.today(), obs_date, raw_value, source_confidence=1.0)
    print("[OK] " + FCODE + "=" + str(raw_value) + " obs=" + str(obs_date))
