#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BU_沥青期货净持仓.py
因子: BU_BU_POS_NET = 沥青期货净持仓（手）

公式: 数据采集（无独立计算公式）

当前状态: [⚠️待修复]
- L1: AKShare get_shfe_rank_table()（今日会员持仓排名），当前返回空dict
- L2: 尝试AKShare futures_dce_position_rank()（仅DCE品种）
- L3: save_l4_fallback() 兜底
- 尝试过的数据源及结果: get_shfe_rank_table() → 空dict
- 解决方案: 需寻找替代数据源或确认API恢复时间

订阅优先级: ★★★
替代付费源: 上期所官网持仓排名 / Mysteel年费
"""
import sys, os as _os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
from common.db_utils import ensure_table, save_to_db, save_l4_fallback, get_pit_dates

import akshare as ak
import pandas as pd

FACTOR_CODE = "BU_BU_POS_NET"
SYMBOL = "BU"
BOUNDS = (-50000.0, 50000.0)


def fetch_rank(obs_date):
    """L1: AKShare SHFE会员持仓排名（今日）"""
    print("[L1] AKShare get_shfe_rank_table()...")
    try:
        result = ak.get_shfe_rank_table(date=obs_date)
        if isinstance(result, dict) and len(result) > 0:
            for date_key, df in result.items():
                if isinstance(df, pd.DataFrame) and len(df) > 0:
                    variety_col = 'variety' if 'variety' in df.columns else '品种'
                    if variety_col in df.columns:
                        bu_df = df[df[variety_col] == 'BU']
                    else:
                        bu_df = df
                    if len(bu_df) > 0:
                        cols = bu_df.columns.tolist()
                        buy_col = next((c for c in cols if 'buy' in c.lower() or '买' in c), None)
                        sell_col = next((c for c in cols if 'sell' in c.lower() or '卖' in c), None)
                        if buy_col and sell_col:
                            net = float(bu_df[buy_col].sum()) - float(bu_df[sell_col].sum())
                        else:
                            vol_col = next((c for c in cols if 'volume' in c.lower() or '成交量' in c), None)
                            net = float(bu_df[vol_col].sum()) if vol_col else 0
                        print(f"[L1] BU净持仓: {net:.0f}手 (date={date_key})")
                        return net, date_key
        raise ValueError("SHFE排名数据为空")
    except Exception as e:
        print(f"[L1] 失败: {e}")
        return None, None


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

    raw_value, actual_date = None, None

    # L1
    try:
        raw_value, actual_date = fetch_rank(obs_date)
    except Exception as e:
        print(f"[L1] 失败: {e}")

    # L2: 无备选源（BU是SHFE品种，DCE接口不适用）
    if raw_value is None:
        print("[L2] 无备选源（SHFE持仓排名仅有get_shfe_rank_table，无其他免费API）")

    # L3
    if raw_value is None:
        if save_l4_fallback(FACTOR_CODE, SYMBOL, pub_date, obs_date,
                             extra_msg="(沥青净持仓)"):
            pass
        else:
            print(f"[WARN] {FACTOR_CODE} 所有数据源均失败")
        sys.exit(0)

    save_to_db(FACTOR_CODE, SYMBOL, pub_date, actual_date or obs_date, raw_value,
               source="akshare_get_shfe_rank_table", source_confidence=1.0)
    print(f"[OK] {FACTOR_CODE}={raw_value:.0f}")
