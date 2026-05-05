#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青期货净持仓.py
因子: BU_POS_NET = 沥青期货净持仓（手）

公式: 前20名多头持仓合计 - 前20名空头持仓合计

当前状态: [✅正常]
- L1: AKShare get_shfe_rank_table(date)，过滤BU品种，计算前20名净持仓
- L2: 无备选源（SHFE持仓排名仅有get_shfe_rank_table）
- L3: save_l4_fallback() 兜底
- bounds: [-50000, 50000]手

订阅优先级: 无需付费
替代付费源: 无
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "BU_POS_NET"
SYMBOL = "BU"
BOUNDS = (-50000.0, 50000.0)


def fetch(obs_date):
    """L1: AKShare SHFE会员持仓排名，过滤BU品种（自动回溯最近交易日）"""
    from datetime import timedelta
    for delta in range(8):
        check = obs_date - timedelta(days=delta)
        if check.weekday() >= 5:
            continue
        date_str = check.strftime("%Y%m%d")
        print(f"[L1] AKShare get_shfe_rank_table(date={date_str})...")
        try:
            result = ak.get_shfe_rank_table(date=date_str)
            if not isinstance(result, dict) or len(result) == 0:
                print(f"[L1] {date_str}: 数据为空")
                continue

            bu_keys = [k for k in result.keys() if 'bu' in k.lower()]
            if not bu_keys:
                print(f"[L1] {date_str}: 无BU品种")
                continue

            total_long = 0.0
            total_short = 0.0
            for k in bu_keys:
                df = result[k]
                if isinstance(df, pd.DataFrame) and len(df) > 0:
                    total_long += float(pd.to_numeric(df['long_open_interest'], errors='coerce').sum())
                    total_short += float(pd.to_numeric(df['short_open_interest'], errors='coerce').sum())

            net = total_long - total_short
            print(f"[L1] BU净持仓: {net:.0f}手 (多头={total_long:.0f}, 空头={total_short:.0f}, date={date_str}, 合约={bu_keys})")
            return net
        except Exception as e:
            print(f"[L1] {date_str}: {e}")
    raise ValueError("所有回溯日期均无BU持仓数据")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    pub_date, obs_date = get_pit_dates()
    if pub_date is None:
        print("-- 非交易日，跳过"); sys.exit(0)

    ensure_table()
    print(f"=== {FACTOR_CODE} === pub={pub_date} obs={obs_date}")

    raw_value = None

    # L1
    try:
        raw_value = fetch(obs_date)
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源
    if raw_value is None:
        print("[L2] 无备选源（SHFE持仓排名仅有get_shfe_rank_table）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青净持仓)"):
            pass
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    if not (BOUNDS[0] <= raw_value <= BOUNDS[1]):
        print(f"[WARN] {FACTOR_CODE}={raw_value} 超出bounds{BOUNDS}，跳过")
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青净持仓)"):
            pass
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, obs_date, raw_value,
               source="akshare_get_shfe_rank_table", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value:.0f}")
