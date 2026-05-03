#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NI_计算基差.py
因子: NI_SPD_BASIS = 沪镍期现基差（元/吨）

公式: NI_SPD_BASIS = 沪镍现货价 - 沪镍期货收盘价

当前状态: [SKIP]永久跳过
- AKShare futures_spot_price(vars_list=['NI']) 只返回到2024-04-30的历史数据，无当前数据
- 无其他可靠免费源获取沪镍现货价
- 不写占位符（obs_date=2024-04-30的数据无参考价值）

订阅优先级: ★★★
替代付费源: Mysteel年费 | SMM年费（沪镍现货报价）
"""
import sys, os
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, get_latest_value
import akshare as ak
from datetime import date, timedelta
import pandas as pd

FACTOR_CODE = "NI_SPD_BASIS"
SYMBOL = "NI"

def fetch():
    df = ak.futures_spot_price(vars_list=["NI"])
    if df.empty:
        raise ValueError("AKShare无NI期现基差数据")
    latest = df.sort_values('date').iloc[-1]
    raw_value = float(latest['near_basis'])
    obs_date = pd.to_datetime(latest['date']).date()
    return raw_value, obs_date

def main():
    try:
        raw_value, obs_date = fetch()
    except Exception as e:
        print("[L1 FAIL] %s: %s" % (FACTOR_CODE, e))
        latest = get_latest_value(FACTOR_CODE, SYMBOL)
        if latest is not None:
            print("[L4 Fallback] %s=%.1f (旧数据，不写入)" % (FACTOR_CODE, latest))
            return
        print("[L4 SKIP] %s: no data" % FACTOR_CODE)
        return

    days_old = (date.today() - obs_date).days
    if days_old > 30:
        print("[SKIP] %s=%.1f obs=%s (滞后%d天，无免费源，不写占位符)" % (FACTOR_CODE, raw_value, obs_date, days_old))
        return

    print("[OK] %s=%.1f obs=%s" % (FACTOR_CODE, raw_value, obs_date))
    save_to_db(FACTOR_CODE, SYMBOL, date.today(), obs_date, raw_value, source_confidence=1.0)

if __name__ == "__main__":
    main()
