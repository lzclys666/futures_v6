#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NR_抓取持仓排名.py
因子: NR_POS_NET = 20号胶期货净持仓(前5)

公式: NR_POS_NET = 前5多头持仓 - 前5空头持仓（手）

当前状态: [✅正常]
- L1: AKShare get_shfe_rank_table — 上期所持仓排名
- L2: 回退最近5个交易日
- L3: 无备源
- L4: save_l4_fallback() DB历史最新值回补
- L5: 不写NULL占位符
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback
import akshare as ak
import pandas as pd
from datetime import timedelta, date

FACTOR_CODE = "NR_POS_NET"
SYMBOL = "NR"
BOUNDS = (-50000, 100000)


def fetch_net(date_str):
    try:
        result = ak.get_shfe_rank_table(date=date_str, vars_list=['NR'])
        if isinstance(result, dict) and result:
            main_contract = list(result.keys())[0]
            df = result[main_contract]
            df['long_open_interest'] = pd.to_numeric(df['long_open_interest'], errors='coerce')
            df['short_open_interest'] = pd.to_numeric(df['short_open_interest'], errors='coerce')
            long5 = df['long_open_interest'].head(5).sum()
            short5 = df['short_open_interest'].head(5).sum()
            return long5 - short5
    except Exception:
        return None


def main():
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    value = None
    obs_str = obs_date.strftime('%Y%m%d')

    # L1: 当前日期
    net = fetch_net(obs_str)
    if net is not None and BOUNDS[0] <= net <= BOUNDS[1]:
        value = float(net)
        print(f"[L1] NR净多头={net:.0f}手")

    # L2: 回退最近5个交易日
    if value is None:
        for delta in range(1, 5):
            prev = (obs_date - timedelta(days=delta)).strftime('%Y%m%d')
            net = fetch_net(prev)
            if net is not None and BOUNDS[0] <= net <= BOUNDS[1]:
                value = float(net)
                print(f"[L2] NR净多头={net:.0f}手 (日期={prev})")
                break

    if value is not None:
        save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, value,
                   source_confidence=1.0, source='akshare_shfe_rank_table')
        print(f"[OK] {FACTOR_CODE}={value:.0f} obs={obs_date}")
    else:
        save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date)


if __name__ == "__main__":
    main()
