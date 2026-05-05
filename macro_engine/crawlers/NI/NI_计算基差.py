#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NI_计算基差.py
因子: NI_SPD_BASIS = 沪镍期现基差（元/吨）

公式: NI_SPD_BASIS = 沪镍现货价 - 沪镍期货收盘价

当前状态: [⚠️待修复]
- L1: AKShare futures_spot_price(vars_list=['NI']) — 数据可能滞后
- L2: 无备源
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符

备注: AKShare现货数据可能滞后30天以上，超期自动跳过不写入
订阅优先级: ★★★
替代付费源: Mysteel年费 | SMM年费（沪镍现货报价）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(this_dir, '..', 'common'))
from db_utils import save_to_db, ensure_table, get_pit_dates, save_l4_fallback
import akshare as ak
from datetime import date
import pandas as pd

FACTOR_CODE = "NI_SPD_BASIS"
SYMBOL = "NI"
BOUNDS = (-5000, 5000)


def fetch():
    df = ak.futures_spot_price(vars_list=["NI"])
    if df.empty:
        raise ValueError("AKShare无NI期现基差数据")
    latest = df.sort_values('date').iloc[-1]
    raw_value = float(latest['near_basis'])
    obs_date = pd.to_datetime(latest['date']).date()
    return raw_value, obs_date


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    try:
        raw_value, obs_date = fetch()
        days_old = (date.today() - obs_date).days
        if days_old > 30:
            print(f"[SKIP] {FACTOR_CODE}={raw_value} obs={obs_date} (滞后{days_old}天，无免费源)")
            save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)
            return
        if BOUNDS[0] <= raw_value <= BOUNDS[1]:
            save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
                       source_confidence=1.0, source='akshare_futures_spot_price')
            print(f"[OK] {FACTOR_CODE}={raw_value} obs={obs_date}")
            return
        else:
            print(f"[WARN] {FACTOR_CODE}={raw_value} out of {BOUNDS}")
    except Exception as e:
        print(f"[L1] {FACTOR_CODE}: {e}")

    save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
