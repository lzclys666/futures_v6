#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算基差
因子: I_SPD_BASIS = 计算基差

公式: 数据采集（无独立计算公式）

当前状态: ⚠️待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date, timedelta

FACTOR_CODE = "I_SPD_BASIS"
SYMBOL = "I"
EXPECTED_MIN = -50
EXPECTED_MAX = 50

def get_last_trading_day():
    today = date.today()
    for days_back in range(7):
        d = today - timedelta(days=days_back)
        if d.weekday() < 5:
            return d
    return today

def fetch():
    obs_date = get_last_trading_day()
    date_str = obs_date.strftime('%Y%m%d')
    df = ak.futures_spot_price(date=date_str, vars_list=['I'])
    if df.empty:
        raise ValueError(f"I现货价返回空 date={date_str}")
    row = df.iloc[0]
    raw_value = float(row['near_basis'])
    return raw_value, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print(f"[L1 FAIL] {FACTOR_CODE}: {e}")
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print(f"[L4 Fallback] {FACTOR_CODE}={latest}")
            return
        print(f"[L4 SKIP] {FACTOR_CODE}: no data")
        return

    if not (EXPECTED_MIN <= raw_value <= EXPECTED_MAX):
        print(f"[WARN] {FACTOR_CODE}={raw_value} out of [{EXPECTED_MIN},{EXPECTED_MAX}]")
        return

    pub_date = date.today()
    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value, source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")

if __name__ == "__main__":
    main()
