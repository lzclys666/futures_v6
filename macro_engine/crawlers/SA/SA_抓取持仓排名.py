#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取持仓排名
因子: 待定义 = 抓取持仓排名

公式: 数据采集（无独立计算公式）

当前状态: [WARN]待修复
- 脚本已有数据获取逻辑，Header待完善
- 尝试过的数据源及结果：需补充
- 解决方案：需补充

订阅优先级: ★★（付费源才需要标注）
替代付费源: 具体平台名称
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.db_utils import ensure_table, save_to_db, get_pit_dates, save_l4_fallback, get_latest_value
import akshare as ak
import pandas as pd

SYMBOL = "SA"

def fetch(obs_date):
    print("[L1] AKShare get_shfe_rank_table SA...")
    date_str = obs_date.strftime("%Y%m%d")
    try:
        data = ak.get_shfe_rank_table(date=date_str, vars_list=["SA"])
        # data = {'rank_list': [...], 'rank_date': '20260417'}
        if isinstance(data, dict) and 'rank_list' in data:
            rank_list = data['rank_list']
            if isinstance(rank_list, list) and len(rank_list) > 0:
                first = rank_list[0]
                if isinstance(first, dict):
                    for k, v in first.items():
                        if hasattr(v, 'columns') and len(v) > 0:
                            df = v
                            print(f"  表格: {k}, 列: {df.columns.tolist()}")
                            long_col, short_col = None, None
                            for c in df.columns:
                                if any(x in str(c) for x in ['多头', 'long', 'Long']):
                                    long_col = c
                                if any(x in str(c) for x in ['空头', 'short', 'Short']):
                                    short_col = c
                            if long_col and short_col:
                                top5_long = df.head(5)[long_col].apply(
                                    lambda x: float(str(x).replace(',','')) if pd.notna(x) else 0).sum()
                                top5_short = df.head(5)[short_col].apply(
                                    lambda x: float(str(x).replace(',','')) if pd.notna(x) else 0).sum()
                                net5 = top5_long - top5_short
                                print(f"[L1] SA前5多={top5_long} 空={top5_short} 净={net5}")
                                return {
                                    "sa_positions_long5": top5_long,
                                    "sa_positions_short5": top5_short,
                                    "sa_positions_net5": net5
                                }
    except Exception as e:
        print(f"[L1] 失败: {e}")
    return {}

if __name__ == "__main__":
    import argparse
    ensure_table()
    pub_date, obs_date = get_pit_dates()
    print(f"(auto) === SA持仓排名 === obs={obs_date}")
    vals = fetch(obs_date)
    for fc, val in vals.items():
        if val is not None:
            save_to_db(fc, SYMBOL, pub_date, obs_date, float(val), source_confidence=1.0, source="akshare_shfe_rank")
            print(f"[OK] {fc}={val} 写入成功")
    if not vals:
        for fc in ["sa_positions_long5", "sa_positions_short5", "sa_positions_net5"]:
            ok = save_l4_fallback(fc, SYMBOL, pub_date, obs_date)
            if ok:
                print(f"[OK] {fc} L4回补成功")
            else:
                print(f"[SKIP] {fc} 今日已有数据或无历史值")
